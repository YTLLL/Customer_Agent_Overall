#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""推理图模块

这个模块实现了推理代理功能，负责处理用户的酒店服务请求。
使用顺序处理流程实现推理，便于后期与其他模块集成。
"""

import os
import json
import logging
import re
from enum import Enum
from typing import Dict, List, Literal, TypedDict, Optional, Union, Any, Tuple

from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, END

from agent.app.models.conversation import Conversation, Message
from agent.app.services.qwen_text_service import QwenTextService
from agent.app.utils.helpers import extract_hotel_name, format_hotel_info
from agent.app.services.gaode_mcp_service import gaode_mcp_service
from agent.app.services.websocket_service import connection_manager

# 定义状态类型
class ReasoningState(TypedDict):
    """推理状态
    
    Attributes:
        conversation: 当前对话对象
        user_message: 用户消息
        hotel_name: 提取的酒店名称
        hotel_info: 获取的酒店信息
        response: 生成的回复
        goal_achieved: 目标是否达成
        error: 错误信息
    """
    conversation: Conversation
    user_message: str
    hotel_name: Optional[str]
    hotel_info: Optional[str]
    response: Optional[str]
    goal_achieved: bool
    error: Optional[str]

# 定义处理步骤类型
class ProcessStep(str, Enum):
    """处理步骤枚举
    
    Attributes:
        EXTRACT_INFO: 信息提取步骤
        GET_HOTEL_INFO: 获取酒店信息步骤
        ANALYZE_REFUND_REQUEST: 分析退票请求步骤
        GENERATE_RESPONSE: 生成回复步骤
        CHECK_GOAL: 检查目标步骤
    """
    EXTRACT_INFO = "extract_info"
    GET_HOTEL_INFO = "get_hotel_info"
    ANALYZE_REFUND_REQUEST = "analyze_refund_request"
    GENERATE_RESPONSE = "generate_response"
    CHECK_GOAL = "check_goal"

# 定义节点类型
class NodeType(str, Enum):
    """节点类型枚举
    
    Attributes:
        EXTRACT_INFO: 信息提取节点
        GET_HOTEL_INFO: 获取酒店信息节点
        ANALYZE_REFUND_REQUEST: 分析退票请求节点
        GENERATE_RESPONSE: 生成回复节点
        CHECK_GOAL: 检查目标节点
    """
    EXTRACT_INFO = "extract_info"
    GET_HOTEL_INFO = "get_hotel_info"
    ANALYZE_REFUND_REQUEST = "analyze_refund_request"
    GENERATE_RESPONSE = "generate_response"
    CHECK_GOAL = "check_goal"

class ReasoningGraph:
    """推理处理流程
    
    这个类实现了一个顺序处理流程，用于处理用户的酒店服务请求。
    流程包含信息提取、获取酒店信息、分析退票请求、生成回复和检查目标五个步骤。
    """
    
    def __init__(self):
        """初始化推理处理流程
        
        初始化通义千问服务和提示模板。
        """
        # 初始化通义千问服务
        self.qwen_service = QwenTextService()
        
        # 初始化提示模板
        self._init_prompts()
        
        # 构建并编译推理图
        self.graph = self._build_graph()
        
        # 推理图功能已经被移至agent_service.py，这里保留基本结构以保证兼容性
    
    def _init_prompts(self) -> None:
        """初始化提示模板
        
        初始化各个节点使用的提示模板。
        """
        # 信息提取提示模板
        self.extract_info_prompt = PromptTemplate(
            input_variables=["user_message"],
            template="""请从以下用户消息中提取关键信息：
            
            用户消息：{user_message}
            
            请提取以下信息：
            1. 酒店名称（如果提到）
            2. 用户的具体需求（换房、退租、退票等）
            3. 用户提供的任何相关细节（房间号、预订信息、订单号等）
            4. 缺失的关键信息（需要用户补充的信息）
            
            如果某项信息未提及，请明确标注为"未提及"。
            
            提取结果："""
        )
        
        # 酒店信息检索提示模板
        self.hotel_info_prompt = PromptTemplate(
            input_variables=["hotel_name"],
            template="""请提供关于以下酒店的信息：
            
            酒店名称：{hotel_name}
            
            请提供以下信息：
            1. 酒店的完整名称
            2. 酒店地址
            3. 联系电话
            4. 退房政策
            5. 退票政策（如果适用）
            
            如果无法找到确切信息，请提供一个合理的模拟回答，以便能够继续对话。
            
            回答："""
        )
        
        # 推理提示模板
        self.reasoning_prompt = PromptTemplate(
            input_variables=["conversation_history", "user_message", "hotel_info"],
            template="""你是一个专门帮助用户处理酒店服务和退票问题的智能助手。
        你的任务是帮助用户解决酒店换房、退租或退票的问题。
        请保持语言简洁、清晰，避免使用复杂术语。
        
        酒店信息：
        {hotel_info}
        
        对话历史：
        {conversation_history}
        
        用户问题：{user_message}
        
        请根据用户的问题和酒店信息提供帮助。如果你需要更多信息，请礼貌地询问。
        如果你认为问题已经解决，请明确告知用户并总结解决方案。
        
        如果用户要求退票，请按照以下步骤处理：
        1. 检查用户提供的信息是否完整（订单号、酒店名称、预订日期等）
        2. 如果信息不完整，请询问用户提供缺失的信息
        3. 如果需要酒店联系方式等外部信息，请根据酒店信息提供或说明需要通过携程获取
        4. 当信息完整后，询问用户是否确认开始退票流程
        5. 如果用户确认，请说明将把信息保存并传递给后续处理系统
        
        请记住：
        1. 使用简单、直接的语言
        2. 提供明确的步骤和指导
        3. 如果需要用户联系酒店，提供具体的联系方式
        4. 避免使用技术术语或复杂的预订系统术语
        
        助手回复："""
        )
        
        # 目标检测提示模板
        self.goal_detection_prompt = PromptTemplate(
            input_variables=["conversation_history", "latest_response"],
            template="""请分析以下对话，判断用户的酒店换房、退租或退票问题是否已经得到解决。
        
        对话历史：
        {conversation_history}
        
        最新回复：
        {latest_response}
        
        如果是退票请求，当满足以下条件时视为已解决：
        1. 用户已提供完整的退票所需信息（订单号、酒店名称、预订日期等）
        2. 用户已确认开始退票流程
        3. 系统已确认将信息保存并传递给后续处理系统
        
        请回答"已解决"或"未解决"，并简要说明理由。
        
        回答："""
        )
    
    def _build_graph(self) -> StateGraph:
        """构建推理图
        
        Returns:
            编译后的状态图
        """
        try:
            # 创建状态图
            graph = StateGraph(ReasoningState)
            
            # 添加节点
            graph.add_node("extract_info", self._extract_info)  # 使用字符串而不是枚举
            graph.add_node("get_hotel_info", self._get_hotel_info)
            graph.add_node("analyze_refund_request", self._analyze_refund_request)
            graph.add_node("generate_response", self._generate_response)
            graph.add_node("check_goal", self._check_goal)
            
            # 设置边 - 定义节点间的流转关系
            graph.add_edge("extract_info", "get_hotel_info")
            graph.add_edge("get_hotel_info", "analyze_refund_request")
            graph.add_edge("analyze_refund_request", "generate_response")
            graph.add_edge("generate_response", "check_goal")
            
            # 设置条件边 - 根据目标达成状态决定流程是否结束
            graph.add_conditional_edges(
                "check_goal",
                self._route_on_goal,
                {
                    "completed": END,  # 目标已完成，结束流程
                    "continue": END    # 目标未完成，但当前对话轮次结束
                }
            )
            
            # 设置入口点 - 使用字符串而不是枚举
            graph.set_entry_point("extract_info")
            
            # 编译图
            compiled_graph = graph.compile()
            return compiled_graph
        except Exception as e:
            print(f"构建推理图时出错: {str(e)}")
            # 返回一个简单的图以避免崩溃
            graph = StateGraph(ReasoningState)
            graph.add_node("generate_response", self._generate_response)
            graph.set_entry_point("generate_response")
            return graph.compile()
    
    async def _extract_info(self, state: ReasoningState) -> ReasoningState:
        """从用户消息中提取关键信息
        
        Args:
            state: 当前推理状态
            
        Returns:
            更新后的推理状态
        """
        try:
            # 提取酒店名称
            hotel_name = extract_hotel_name(state["user_message"])
            
            # 判断是否是退票请求
            is_refund_request = "退票" in state["user_message"] or "退款" in state["user_message"] or "退订" in state["user_message"]
            
            # 更新状态
            state["hotel_name"] = hotel_name
            state["is_refund_request"] = is_refund_request
            return state
        except Exception as e:
            # 记录错误并返回更新后的状态
            state["error"] = f"提取信息错误: {str(e)}"
            return state
    
    async def _get_hotel_info(self, state: ReasoningState) -> ReasoningState:
        """获取酒店信息
        
        Args:
            state: 当前推理状态
            
        Returns:
            更新后的推理状态，包含酒店信息
        """
        try:
            hotel_name = state.get("hotel_name")
            if not hotel_name:
                # 未识别到酒店名称时的处理
                state["hotel_info"] = "未能识别酒店名称，请提供更多信息。"
                return state
            
            # 使用高德地图MCP服务获取酒店信息
            hotel_data = await gaode_mcp_service.search_hotel(hotel_name)
            
            # 格式化酒店信息
            hotel_info = f"酒店名称：{hotel_data.get('name', '未知')}\n"
            hotel_info += f"酒店地址：{hotel_data.get('formatted_address', '未知')}\n"
            hotel_info += f"联系电话：{hotel_data.get('tel', '未知')}\n"
            
            # 添加退房和退票政策
            policies = hotel_data.get('policies', {})
            if policies:
                hotel_info += f"退房政策：{policies.get('check_out', '未知')}\n"
                hotel_info += f"取消政策：{policies.get('cancellation', '未知')}\n"
                hotel_info += f"退款政策：{policies.get('refund', '未知')}"
            
            # 更新状态
            state["hotel_info"] = hotel_info
            return state
        except Exception as e:
            # 记录错误并返回更新后的状态
            state["error"] = f"获取酒店信息错误: {str(e)}"
            return state
    
    async def _analyze_refund_request(self, state: ReasoningState) -> ReasoningState:
        """分析退票请求
        
        Args:
            state: 当前推理状态
            
        Returns:
            更新后的推理状态
        """
        try:
            # 如果不是退票请求，直接返回
            if not state.get("is_refund_request", False):
                return state
            
            # 调用高德MCP服务分析退票请求
            user_message = state["user_message"]
            analysis_result = await gaode_mcp_service.analyze_refund_request(user_message)
            
            # 获取提取的信息
            extracted_info = analysis_result.get("extracted_info", {})
            missing_fields = analysis_result.get("missing_fields", [])
            is_complete = analysis_result.get("is_complete", False)
            hotel_info = analysis_result.get("hotel_info", {})
            
            # 将提取的信息添加到conversation的元数据中
            if "refund_info" not in state["conversation"].metadata:
                state["conversation"].metadata["refund_info"] = {}
            
            # 更新refund_info
            refund_info = state["conversation"].metadata["refund_info"]
            for field, value in extracted_info.items():
                if value and value != "缺失":
                    refund_info[field] = value
            
            # 添加酒店信息
            if hotel_info:
                refund_info["hotel_info"] = hotel_info
            
            # 更新状态
            state["is_refund_complete"] = is_complete
            state["missing_fields"] = missing_fields
            
            # 如果信息不完整，生成缺失信息提示
            if not is_complete:
                # 字段名称映射
                field_name_map = {
                    "hotel_name": "酒店名称",
                    "order_id": "订单号",
                    "check_in_date": "入住日期",
                    "guest_name": "客人姓名"
                }
                
                # 将字段名称转换为中文
                missing_fields_zh = [field_name_map.get(field, field) for field in missing_fields]
                missing_fields_str = ", ".join(missing_fields_zh)
                
                prompt = f"为了帮助您退票，我们需要以下信息：{missing_fields_str}。请提供这些信息，以便我们继续处理您的退票请求。"
                state["missing_info_prompt"] = prompt
            
            # 打印调试信息
            print(f"退票信息分析结果: {analysis_result}")
            print(f"更新后的退票信息: {refund_info}")
            
            return state
        except Exception as e:
            # 记录错误并返回更新后的状态
            state["error"] = f"分析退票请求错误: {str(e)}"
            return state
    
    async def _generate_response(self, state: ReasoningState) -> ReasoningState:
        """生成回复
        
        Args:
            state: 当前推理状态
            
        Returns:
            更新后的推理状态，包含生成的回复
        """
        try:
            # 获取用户ID用于发送WebSocket消息
            user_id = state["conversation"].user_id
            
            # 如果有错误，生成错误回复
            if "error" in state:
                error_msg = state["error"]
                feedback_type = "error"
                
                if "获取酒店信息错误" in error_msg:
                    response = "抱歉，我无法获取该酒店的信息。请确认酒店名称是否正确，或者提供更多的酒店详细信息。"
                    metadata = {"error_type": "hotel_info_error"}
                elif "分析退票请求错误" in error_msg:
                    response = "抱歉，我无法分析您的退票请求。请以更清晰的方式提供您的退票信息，包括酒店名称、订单号、入住日期和客人姓名。"
                    metadata = {"error_type": "refund_request_error"}
                else:
                    response = f"抱歉，处理您的请求时出现问题。请稍后再试。"
                    metadata = {"error_type": "general_error", "details": error_msg}
                
                # 发送WebSocket消息
                await connection_manager.broadcast_feedback(user_id, feedback_type, response, metadata)
                
                state["response"] = response
                return state
            
            # 如果是退票请求但信息不完整，返回缺失信息提示
            if state.get("is_refund_request", False) and not state.get("is_refund_complete", False):
                if "missing_info_prompt" in state:
                    response = state["missing_info_prompt"]
                    
                    # 获取缺失的字段
                    missing_fields = []
                    if "missing_fields" in state:
                        missing_fields = state["missing_fields"]
                    
                    # 发送WebSocket消息
                    metadata = {
                        "missing_fields": missing_fields,
                        "request_type": "refund"
                    }
                    await connection_manager.broadcast_feedback(user_id, "info", response, metadata)
                    
                    state["response"] = response
                    return state
            
            # 如果是完整的退票请求，生成确认信息
            if state.get("is_refund_request", False) and state.get("is_refund_complete", True):
                refund_info = state["conversation"].metadata.get("refund_info", {})
                hotel_info = refund_info.get("hotel_info", {})
                
                confirmation = f"我已收到您的退票请求，信息如下：\n"
                confirmation += f"酒店名称：{refund_info.get('hotel_name', '未提供')}\n"
                confirmation += f"订单号：{refund_info.get('order_id', '未提供')}\n"
                confirmation += f"入住日期：{refund_info.get('check_in_date', '未提供')}\n"
                confirmation += f"客人姓名：{refund_info.get('guest_name', '未提供')}\n"
                
                if hotel_info:
                    confirmation += f"\n酒店联系电话：{hotel_info.get('tel', '未知')}\n"
                    if 'policies' in hotel_info and 'refund' in hotel_info['policies']:
                        confirmation += f"退款政策：{hotel_info['policies']['refund']}\n"
                
                confirmation += "\n根据酒店政策，退款将在处理完成后的7-15个工作日内退回到您的原支付账户。\n\n"
                confirmation += "请确认以上信息是否正确？如果正确，我将立即为您处理退票请求。"
                
                # 发送WebSocket消息
                metadata = {
                    "refund_info": refund_info,
                    "hotel_info": hotel_info,
                    "request_type": "refund_confirmation"
                }
                await connection_manager.broadcast_feedback(user_id, "success", confirmation, metadata)
                
                state["response"] = confirmation
                return state
            
            # 其他情况，使用模板生成回复
            hotel_info = state.get("hotel_info", "没有酒店信息")
            user_message = state["user_message"]
            conversation_history = state.get("conversation_history", "")
            
            # 使用推理提示模板生成回复
            response = self.reasoning_chain.run(
                conversation_history=conversation_history,
                user_message=user_message,
                hotel_info=hotel_info
            )
            
            # 发送WebSocket消息
            metadata = {
                "has_hotel_info": hotel_info != "没有酒店信息",
                "request_type": "general_query"
            }
            await connection_manager.broadcast_feedback(user_id, "info", response, metadata)
            
            # 更新状态
            state["response"] = response
            return state
        except Exception as e:
            # 记录错误并返回更新后的状态
            error_msg = f"生成回复错误: {str(e)}"
            state["error"] = error_msg
            response = "抱歉，处理您的请求时出现问题。请稍后再试。"
            state["response"] = response
            
            # 尝试发送WebSocket错误消息
            try:
                user_id = state["conversation"].user_id
                metadata = {"error_type": "response_generation_error", "details": str(e)}
                await connection_manager.broadcast_feedback(user_id, "error", response, metadata)
            except Exception:
                # 如果发送WebSocket消息失败，忽略该错误
                pass
                
            return state
    
    async def _check_goal(self, state: ReasoningState) -> ReasoningState:
        """检查对话目标是否达成
        
        Args:
            state: 当前推理状态
            
        Returns:
            更新后的推理状态，包含目标达成状态
        """
        try:
            # 准备对话历史
            conversation_history = self._format_conversation_history(state["conversation"])
            
            # 检测目标是否达成
            prompt = self.goal_detection_prompt.format(
                conversation_history=conversation_history,
                latest_response=state["response"]
            )
            result = await self.qwen_service.analyze_text(conversation_history, prompt)
            response = result.get("raw_response", "目标检测失败")
            
            # 解析响应
            goal_achieved = "已解决" in response
            
            # 更新状态
            state["goal_achieved"] = goal_achieved
            return state
        except Exception as e:
            state["error"] = f"检查目标错误: {str(e)}"
            return state
    
    def _route_on_goal(self, state: ReasoningState) -> Literal["completed", "continue"]:
        """根据目标达成状态路由
        
        Args:
            state: 当前推理状态
            
        Returns:
            路由决策："completed" 或 "continue"
        """
        if state.get("goal_achieved", False):
            return "completed"
        return "continue"
    
    def _format_conversation_history(self, conversation: Conversation) -> str:
        """格式化对话历史
        
        Args:
            conversation: 对话对象
            
        Returns:
            格式化后的对话历史字符串
        """
        history = ""
        for msg in conversation.messages:
            role = "用户" if msg.role == "user" else "助手"
            history += f"{role}: {msg.content}\n\n"
        return history
    
    async def process_request(self, conversation: Conversation, user_message: str) -> str:
        """处理用户请求并生成回复
        
        Args:
            conversation: 对话对象
            user_message: 用户消息
            
        Returns:
            生成的回复字符串
        """
        print("开始处理用户请求...")
        
        try:
            # 初始化状态
            initial_state: ReasoningState = {
                "conversation": conversation,
                "user_message": user_message,
                "hotel_name": None,
                "hotel_info": None,
                "response": None,
                "goal_achieved": False,
                "error": None
            }
            
            # 使用通义千问API生成回复
            try:
                print("使用通义千问API生成回复...")
                
                # 构建提示
                prompt = f"""您是一位专业的酒店客服，请根据用户消息生成合适的回复：
                
                用户消息: {user_message}
                
                如果用户请求换房，请询问必要的信息（如订单号、当前房间号、希望更换的房型、更换原因等）。
                如果用户请求退款，请询问必要的信息（如订单号、酒店名称、入住日期、客人姓名等）。
                
                请使用礼貌、专业的语气。
                """
                
                response = await self.qwen_service.analyze_text(user_message, prompt)
                return response.get('raw_response', "抱歉，我无法处理您的请求，请稍后再试。")
                
            except Exception as api_error:
                print(f"API调用错误: {str(api_error)}")
                
                # 如果API调用失败，使用简单的备用逻辑
                if "换房" in user_message or "换一间" in user_message or "双床房" in user_message or "大床房" in user_message:
                    # 构建换房回复
                    response_parts = []
                    
                    # 确认已知信息
                    if context.get("hotel_name") and context.get("room_number"):
                        response_parts.append(f"您好，我已收到您在{context['hotel_name']}的{context['room_number']}房间的换房请求。")
                    elif context.get("hotel_name"):
                        response_parts.append(f"您好，我已收到您在{context['hotel_name']}的换房请求。")
                    elif context.get("room_number"):
                        response_parts.append(f"您好，我已收到您关于{context['room_number']}房间的换房请求。")
                    else:
                        response_parts.append("您好，我已收到您的换房请求。")
                    
                    # 确认已知的房间类型
                    if context.get("room_type"):
                        response_parts.append(f"我们会尽力为您安排{context['room_type']}。")
                    
                    # 确认已知的更换原因
                    if context.get("change_reason"):
                        response_parts.append(f"我理解您的更换原因是{context['change_reason']}。")
                    
                    # 询问缺失的信息
                    missing_info = []
                    if not context.get("order_number"):
                        missing_info.append("您当前的订单号")
                    if not context.get("room_type"):
                        missing_info.append("您希望更换的房间类型")
                    if not context.get("change_reason"):
                        missing_info.append("更换的原因")
                    
                    if missing_info:
                        response_parts.append("为了更好地为您服务，请提供以下信息：")
                        for i, info in enumerate(missing_info, 1):
                            response_parts.append(f"{i}. {info}")
                    else:
                        # 如果所有信息已提供，则确认处理
                        response_parts.append("我们已收到您的所有信息，正在处理您的换房请求。我们将尽快为您安排新的房间。")
                    
                    # 添加结尾语
                    response_parts.append("我们将尽快处理您的请求，并为您提供可用的房间选项。")
                    
                    # 生成最终回复
                    return "\n".join(response_parts)
                
                elif "退票" in user_message or "退款" in user_message or "取消预订" in user_message:
                    # 构建退款回复
                    response_parts = []
                    
                    # 确认已知信息
                    if context.get("hotel_name"):
                        response_parts.append(f"您好，我已收到您关于{context['hotel_name']}的退款请求。")
                    else:
                        response_parts.append("您好，我已收到您的退款请求。")
                    
                    # 询问缺失的信息
                    missing_info = []
                    if not context.get("hotel_name"):
                        missing_info.append("酒店名称")
                    if not context.get("order_number"):
                        missing_info.append("订单号")
                    
                    if missing_info:
                        response_parts.append("为了更好地为您处理退款请求，请提供以下信息：")
                        for i, info in enumerate(missing_info, 1):
                            response_parts.append(f"{i}. {info}")
                        response_parts.append("还请提供入住日期和客人姓名等信息，以便我们更好地为您服务。")
                    else:
                        # 如果所有信息已提供，则确认处理
                        response_parts.append("我们已收到您的所有信息，正在处理您的退款请求。我们将在工作日内完成退款处理。")
                    
                    # 生成最终回复
                    return "\n".join(response_parts)
                
                else:
                    return "您好，我是酒店服务助手。请问有什么可以帮助您的吗？"
                
        except Exception as e:
            # 处理其他异常
            print(f"处理请求时发生异常: {str(e)}")
            return f"抱歉，系统处理您的请求时遇到了技术问题: {str(e)}"