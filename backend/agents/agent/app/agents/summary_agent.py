"""总结代理模块

这个模块实现了对话总结代理功能，负责生成对话的摘要和结论。
"""

import os
from typing import Dict, Any, Optional
import json

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agent.app.models.conversation import Conversation
from agent.app.services.qwen_text_service import QwenTextService
from agent.app.services.db_service import DBService

class SummaryAgent:
    """总结代理类，负责生成对话摘要和结论"""
    
    def __init__(self):
        """初始化总结代理"""
        # 初始化通义千问文本理解服务
        self.qwen_service = QwenTextService()
        # 初始化数据库服务
        self.db_service = DBService()
        self._init_prompts()
    
    def _init_prompts(self):
        """初始化提示模板"""
        # 对话总结提示模板
        self.summary_prompt = """请总结以下关于酒店服务问题的对话。
        
        对话历史：
        {conversation_history}
        
        问题是否解决：{goal_achieved}
        
        请提供一个简洁的总结，包括：
        1. 用户的主要问题
        2. 问题解决的过程
        3. 最终解决方案或后续步骤
        4. 可能的改进建议
        
        总结应该简洁明了，适合中老年阅读理解。
        
        总结："""
        
        # 退票需求的prompt生成模板
        self.refund_prompt_template = """请根据以下退票请求的信息，生成一个结构化的提示，供后续的退票处理使用。
        
        退票请求信息：
        - 酒店名称：{hotel_name}
        - 订单号：{order_id}
        - 入住日期：{check_in_date}
        - 客人姓名：{guest_name}
        - 酒店电话：{hotel_tel}
        - 退款政策：{refund_policy}
        
        请生成一个结构化的提示，包含以下内容：
        1. 退票请求的目的和背景
        2. 需要联系的酒店信息
        3. 退款的具体操作步骤
        4. 需要当前客服代表关注的特殊情况或注意事项
        
        提示应该简洁明确，但要包含所有必要的信息，以便客服代表能够高效地处理退票请求。
        
        生成的提示："""
    
    def _format_conversation_history(self, conversation: Conversation) -> str:
        """格式化对话历史"""
        history = ""
        for msg in conversation.messages:
            role = "用户" if msg.role == "user" else "助手"
            history += f"{role}: {msg.content}\n\n"
        return history
    
    async def generate_summary(self, conversation: Conversation) -> dict:
        """生成对话总结"""
        # 准备对话历史
        conversation_history = self._format_conversation_history(conversation)
        # 确定目标是否达成
        goal_achieved = "是" if conversation.goal_achieved else "否"
        prompt = self.summary_prompt.format(conversation_history=conversation_history, goal_achieved=goal_achieved)
        result = await self.qwen_service.analyze_text(conversation_history, prompt)
        summary = result.get("raw_response", "总结生成失败")
        
        # 如果是退票请求，则生成退票prompt并存储
        refund_prompt = None
        if self._is_refund_request(conversation):
            refund_prompt = await self._generate_refund_prompt(conversation)
            if refund_prompt:
                # 将退票prompt存储到元数据中
                conversation.metadata["refund_prompt"] = refund_prompt
                # 保存到MongoDB
                self.db_service.save_conversation(conversation)
        
        return {
            "summary": summary.strip(),
            "goal_achieved": conversation.goal_achieved,
            "turns": len([msg for msg in conversation.messages if msg.role == "user"]),
            "duration_minutes": (conversation.updated_at - conversation.created_at).total_seconds() / 60,
            "refund_prompt": refund_prompt
        }
    
    def _is_refund_request(self, conversation: Conversation) -> bool:
        """判断是否是退票请求"""
        # 检查元数据中是否有refund_info
        if "refund_info" in conversation.metadata:
            return True
        
        # 检查对话中是否有退票相关关键词
        for msg in conversation.messages:
            if msg.role == "user" and ("退票" in msg.content or "退款" in msg.content or "退订" in msg.content):
                return True
        
        return False
    
    async def _generate_refund_prompt(self, conversation: Conversation) -> Optional[str]:
        """生成退票prompt"""
        # 获取退票信息
        refund_info = conversation.metadata.get("refund_info", {})
        if not refund_info:
            return None
        
        # 获取酒店信息
        hotel_info = refund_info.get("hotel_info", {})
        
        # 准备参数
        params = {
            "hotel_name": refund_info.get("hotel_name", "未提供"),
            "order_id": refund_info.get("order_id", "未提供"),
            "check_in_date": refund_info.get("check_in_date", "未提供"),
            "guest_name": refund_info.get("guest_name", "未提供"),
            "hotel_tel": hotel_info.get("tel", "未提供"),
            "refund_policy": hotel_info.get("policies", {}).get("refund", "未提供")
        }
        
        # 生成prompt
        prompt_template = self.refund_prompt_template.format(**params)
        
        # 将退票信息转换为文本格式作为输入
        text_input = f"退票请求信息:\n"
        text_input += f"酒店名称: {params['hotel_name']}\n"
        text_input += f"订单号: {params['order_id']}\n"
        text_input += f"入住日期: {params['check_in_date']}\n"
        text_input += f"客人姓名: {params['guest_name']}\n"
        text_input += f"酒店电话: {params['hotel_tel']}\n"
        text_input += f"退款政策: {params['refund_policy']}\n"
        
        # 调用API生成prompt
        result = await self.qwen_service.analyze_text(text_input, prompt_template)
        refund_prompt = result.get("raw_response", "")
        
        return refund_prompt.strip() if refund_prompt else None
    
    async def process_refund_request(self, conversation: Conversation) -> Dict[str, Any]:
        """处理退票请求，生成prompt并存储到MongoDB"""
        # 生成退票prompt
        refund_prompt = await self._generate_refund_prompt(conversation)
        
        if not refund_prompt:
            return {
                "success": False,
                "message": "无法生成退票prompt，请确保提供了完整的退票信息"
            }
        
        # 将prompt存储到元数据中
        conversation.metadata["refund_prompt"] = refund_prompt
        
        # 记录日志
        print(f"生成的退票prompt: {refund_prompt}")
        
        # 保存到MongoDB
        self.db_service.save_conversation(conversation)
        
        return {
            "success": True,
            "message": "退票prompt已生成并存储",
            "refund_prompt": refund_prompt
        }