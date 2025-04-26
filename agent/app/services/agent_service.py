"""代理服务模块

这个模块提供了推理代理的核心功能，负责处理用户请求和生成回复。
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agent.app.models.conversation import Conversation, Message, ConversationStatus
from agent.app.services.db_service import DBService
from agent.app.services.qwen_text_service import QwenTextService

class AgentService:
    """代理服务类，负责处理用户请求和生成回复"""
    
    def __init__(self):
        """初始化代理服务"""
        # 初始化数据库服务
        self.db_service = DBService()
        # 初始化通义千问文本理解服务
        self.qwen_service = QwenTextService()
        # 设置最大对话轮次
        self.max_turns = int(os.getenv("MAX_CONVERSATION_TURNS", "10"))
        # 设置对话超时时间（小时）
        self.timeout_hours = int(os.getenv("CONVERSATION_TIMEOUT_HOURS", "6"))
        # 初始化对话上下文记忆字典
        # 格式: {conversation_id: {"hotel_name": xxx, "room_number": xxx, ...}}
        self.conversation_contexts = {}
        # 初始化提示模板
        self._init_prompts()

    def _init_prompts(self):
        """初始化提示模板"""
        # 对话提示模板
        self.conversation_prompt = """你是一个专门帮助用户处理酒店服务和退票问题的智能助手。
        你的任务是帮助用户解决酒店换房、退租或退票的问题。
        请保持语言简洁、清晰，避免使用复杂术语。
        
        对话历史：
        {conversation_history}
        
        用户问题：{user_message}
        
        请根据用户的问题提供帮助。如果你需要更多信息，请礼貌地询问。
        如果你认为问题已经解决，请明确告知用户并总结解决方案。
        
        如果用户要求退票，请按照以下步骤处理：
        1. 检查用户提供的信息是否完整（订单号、酒店名称、预订日期等）
        2. 如果信息不完整，请询问用户提供缺失的信息
        3. 如果需要酒店联系方式等外部信息，请说明需要通过携程获取
        4. 当信息完整后，询问用户是否确认开始退票流程
        5. 如果用户确认，请说明将把信息保存并传递给后续处理系统
        
        助手回复："""
        # 目标检测提示模板
        self.goal_detection_prompt = """请分析以下对话，判断用户的酒店换房、退租或退票问题是否已经得到解决。
        
        对话历史：
        {conversation_history}
        
        如果是退票请求，当满足以下条件时视为已解决：
        1. 用户已提供完整的退票所需信息（订单号、酒店名称、预订日期等）
        2. 用户已确认开始退票流程
        3. 系统已确认将信息保存并传递给后续处理系统
        
        请回答"已解决"或"未解决"，并简要说明理由。
        
        回答："""
        # 对话总结提示模板
        self.summary_prompt = """请总结以下关于酒店服务或退票问题的对话。
        
        对话历史：
        {conversation_history}
        
        请提供一个简洁的总结，包括：
        1. 用户的主要问题（换房、退租或退票）
        2. 问题是否得到解决
        3. 解决方案或后续步骤
        4. 如果是退票请求，请特别注明已收集的关键信息
        
        总结："""

    async def process_message(self, conversation_id: str, user_message: str) -> None:
        """处理用户消息并生成回复"""
        # 获取对话
        conversation = self.db_service.get_conversation(conversation_id)
        if not conversation:
            return
            
        # 检查对话是否已超过最大轮次
        if len(conversation.messages) >= self.max_turns * 2:
            final_message = Message(
                role="assistant",
                content="很抱歉，我们的对话已经进行了较长时间。为了更好地解决您的问题，建议您直接联系酒店前台或客服电话。感谢您的理解。"
            )
            conversation.add_message(final_message)
            self.db_service.save_message(conversation.id, final_message)
            conversation.status = ConversationStatus.COMPLETED
            self.db_service.update_conversation(conversation)
            return
            
        # 检查对话是否超时
        if conversation.is_timeout(self.timeout_hours):
            conversation.status = ConversationStatus.TIMEOUT
            self.db_service.update_conversation(conversation)
            return
            
        # 从用户消息中提取关键信息
        # 获取当前对话的上下文记忆
        context = self.conversation_contexts.get(conversation_id, {})
        print(f"当前对话上下文: {context}")
        
        # 使用千问API分析用户意图
        user_intent = await self._analyze_user_intent(user_message)
        print(f"用户意图分析结果: {user_intent}")
        
        # 检查用户是否在询问酒店信息
        is_asking_hotel_info = user_intent.get('is_asking_hotel_info', False)
        if is_asking_hotel_info:
            print("用户正在询问酒店信息")
        
        # 使用千问API判断用户提到的实体是否是酒店或宾馆
        print(f"用户意图分析结果: {user_intent}")
        hotel_name = user_intent.get('hotel_name')
        
        # 如果千问API没有识别出酒店名称，尝试使用正则表达式提取
        if not hotel_name and ("酒店" in user_message or "宾馆" in user_message):
            import re
            # 尝试匹配完整的酒店名称，如"广州汉庭酒店"
            hotel_pattern = re.compile(r"([\u4e00-\u9fa5a-zA-Z]+(?:酒店|宾馆))")
            hotel_match = hotel_pattern.search(user_message)
            if hotel_match:
                hotel_name = hotel_match.group(1)
                print(f"通过正则表达式提取到酒店名称: {hotel_name}")
            else:
                # 尝试提取地名+酒店的组合
                location_pattern = re.compile(r"([\u4e00-\u9fa5]+)(?:的|在)?(?:酒店|宾馆)")
                location_match = location_pattern.search(user_message)
                if location_match:
                    location = location_match.group(1)
                    hotel_name = f"{location}酒店"  # 假设用户想查询的是该地区的酒店
                    print(f"提取到地点+酒店的组合: {hotel_name}")
        
        if hotel_name:
            context["hotel_name"] = hotel_name
            print(f"最终确定的酒店名称: {hotel_name}")
            
            # 使用高德MCP服务获取真实酒店信息
            from agent.app.services.gaode_mcp_service import gaode_mcp_service
            print(f"开始使用高德MCP服务获取酒店信息: {hotel_name}")
            try:
                hotel_info = await gaode_mcp_service.search_hotel(hotel_name)
                print(f"高德MCP服务返回结果: {hotel_info}")
                
                if hotel_info:
                    # 检查是否返回了多个酒店选项
                    if hotel_info.get("multiple_options"):
                        print(f"找到多家{hotel_name}，需要用户选择")
                        context["multiple_hotels"] = hotel_info["hotels"]
                        context["hotel_selection_needed"] = True
                        context["hotel_selection_message"] = hotel_info["message"]
                    else:
                        # 将酒店信息保存到上下文中
                        context["hotel_info"] = hotel_info
                        print(f"成功获取酒店信息: {hotel_info}")
                        
                        # 检查是否是因为API调用失败而返回的默认信息
                        if hotel_info.get("api_call_failed"):
                            print("警告: API调用失败，使用默认酒店信息")
                else:
                    print("未能获取酒店信息，高德MCP服务返回空结果")
            except Exception as e:
                print(f"调用高德MCP服务时出错: {str(e)}")
        
        # 提取房间号
        import re
        room_pattern = re.compile(r"\d{3,4}")
        room_matches = room_pattern.findall(user_message)
        if room_matches:
            room_number = room_matches[0]
            context["room_number"] = room_number
            print(f"提取到房间号: {room_number}")
        
        # 提取房间类型
        room_types = ["双床房", "大床房", "单人房", "套房", "家庭房"]
        for rt in room_types:
            if rt in user_message:
                context["room_type"] = rt
                print(f"提取到房间类型: {rt}")
                break
        
        # 提取更换原因
        if "太吵" in user_message:
            context["change_reason"] = "房间太吵"
            print(f"提取到更换原因: 房间太吵")
        
        # 检查用户是否在选择酒店
        if context.get("hotel_selection_needed") and context.get("multiple_hotels"):
            # 尝试从用户消息中提取酒店选择
            selected_hotel = None
            hotels_list = context["multiple_hotels"]
            
            # 尝试通过序号选择
            import re
            number_match = re.search(r'\d+', user_message)
            if number_match:
                try:
                    selection_index = int(number_match.group()) - 1
                    if 0 <= selection_index < len(hotels_list):
                        selected_hotel = hotels_list[selection_index]
                        print(f"用户选择了第{selection_index+1}个酒店: {selected_hotel['name']}")
                except:
                    pass
            
            # 如果没有找到序号，尝试通过酒店名称匹配
            if not selected_hotel:
                for hotel in hotels_list:
                    if hotel["name"] in user_message:
                        selected_hotel = hotel
                        print(f"用户选择了酒店: {hotel['name']}")
                        break
            
            # 如果找到了用户选择的酒店，获取详细信息
            if selected_hotel:
                from agent.app.services.gaode_mcp_service import gaode_mcp_service
                hotel_name = selected_hotel["name"]
                print(f"获取用户选择的酒店详细信息: {hotel_name}")
                hotel_info = await gaode_mcp_service.search_hotel(hotel_name)
                if hotel_info and not hotel_info.get("multiple_options"):
                    context["hotel_info"] = hotel_info
                    context["hotel_name"] = hotel_name
                    context["hotel_selection_needed"] = False
                    del context["multiple_hotels"]
                    print(f"成功获取酒店详细信息: {hotel_info}")
    
        # 如果用户正在询问酒店信息，但上下文中有酒店名称而没有酒店信息，尝试获取酒店信息
        if is_asking_hotel_info and context.get("hotel_name") and not context.get("hotel_info"):
            from agent.app.services.gaode_mcp_service import gaode_mcp_service
            hotel_name = context["hotel_name"]
            print(f"用户询问酒店信息，尝试获取酒店信息: {hotel_name}")
            hotel_info = await gaode_mcp_service.search_hotel(hotel_name)
            if hotel_info:
                # 检查是否返回了多个酒店选项
                if hotel_info.get("multiple_options"):
                    print(f"找到多家{hotel_name}，需要用户选择")
                    context["multiple_hotels"] = hotel_info["hotels"]
                    context["hotel_selection_needed"] = True
                    context["hotel_selection_message"] = hotel_info["message"]
                else:
                    context["hotel_info"] = hotel_info
                    print(f"成功获取酒店信息: {hotel_info}")
                    
                    # 检查是否是因为API调用失败而返回的默认信息
                    if hotel_info.get("api_call_failed"):
                        print("警告: 高德API调用失败，使用默认信息")
    
        # 更新对话上下文
        self.conversation_contexts[conversation_id] = context
        print(f"更新后的对话上下文: {self.conversation_contexts[conversation_id]}")
        
        # 准备对话历史
        conversation_history = self._format_conversation_history(conversation)
        
        # 构建上下文信息字符串
        context_info = ""
        
        # 如果需要酒店选择，添加酒店选项信息
        if context.get("hotel_selection_needed") and context.get("multiple_hotels"):
            context_info += f"需要选择酒店: {context.get('hotel_selection_message', '')}\n"
            context_info += "酒店选项:\n"
            for i, hotel in enumerate(context["multiple_hotels"]):
                context_info += f"{i+1}. {hotel['name']} - {hotel.get('district', '')} {hotel.get('formatted_address', '')}\n"
            context_info += "请用户选择一家酒店或提供更准确的酒店名称\n\n"
        
        # 添加其他上下文信息
        if context.get("hotel_name"):
            context_info += f"酒店名称: {context['hotel_name']}\n"
        if context.get("room_number"):
            context_info += f"房间号: {context['room_number']}\n"
        if context.get("room_type"):
            context_info += f"目标房间类型: {context['room_type']}\n"
        if context.get("change_reason"):
            context_info += f"更换原因: {context['change_reason']}\n"
        if context.get("order_number"):
            context_info += f"订单号: {context['order_number']}\n"
        
        # 添加酒店详细信息
        hotel_info_str = ""
        if context.get("hotel_info") and not context.get("hotel_selection_needed"):
            hotel_info = context["hotel_info"]
            hotel_info_str += "\n酒店详细信息:\n"
            
            # 检查是否是因为API调用失败而返回的默认信息
            if hotel_info.get("api_call_failed"):
                hotel_info_str += "注意: 以下信息为默认信息，可能与实际情况有差异。\n"
            
            # 添加酒店名称
            hotel_info_str += f"酒店名称: {hotel_info.get('name', '')}\n"
            
            # 添加酒店地址
            hotel_info_str += f"地址: {hotel_info.get('formatted_address', '')}\n"
            
            # 添加酒店电话，确保不会使用虚假电话
            tel_info = hotel_info.get('tel', '')
            if tel_info and tel_info != "请咨询酒店前台或客服中心":
                hotel_info_str += f"电话: {tel_info}\n"
            else:
                hotel_info_str += "电话: 请咨询酒店前台或客服中心\n"
            
            # 添加酒店政策信息
            if 'policies' in hotel_info:
                policies = hotel_info['policies']
                hotel_info_str += "酒店政策:\n"
                hotel_info_str += f"- 入住时间: {policies.get('check_in', '')}\n"
                hotel_info_str += f"- 退房时间: {policies.get('check_out', '')}\n"
                hotel_info_str += f"- 取消政策: {policies.get('cancellation', '')}\n"
                hotel_info_str += f"- 退款政策: {policies.get('refund', '')}\n"
    
        # 生成回复
        enhanced_prompt = f"""您是一位专业的酒店客服，请根据以下用户消息和已知上下文信息生成合适的回复：

对话历史：
{conversation_history}

用户问题：{user_message}

已知上下文信息：
{context_info}
{hotel_info_str}

如果用户请求换房，请先确认已知信息，然后只询问缺失的信息（如订单号、当前房间号、希望更换的房型、更换原因等）。
如果用户请求退款，请先确认已知信息，然后只询问缺失的信息（如订单号、酒店名称、入住日期、客人姓名等）。

如果用户询问酒店信息（如电话、地址等），请根据上下文中的酒店信息提供准确回答。如果信息不可用或不确定，请告知用户可以联系酒店前台或客服中心获取最新信息，不要提供虚假的电话号码或地址。

如果所有必要信息已提供，请确认您将处理请求并提供具体的后续步骤。
请使用礼貌、专业的语气。

助手回复："""
        
        result = await self.qwen_service.analyze_text(user_message, enhanced_prompt)
        response = result.get("raw_response", "对话生成失败")
        assistant_message = Message(
            role="assistant",
            content=response.strip()
        )
        conversation.add_message(assistant_message)
        self.db_service.save_message(conversation.id, assistant_message)
    
        # 检查目标是否达成
        try:
            if len(conversation.messages) >= 4:
                goal_achieved = await self._check_goal_achieved(conversation)
                conversation.goal_achieved = goal_achieved
                if goal_achieved:
                    conversation.status = ConversationStatus.COMPLETED
        except Exception as e:
            print(f"检查目标是否达成时出错: {str(e)}")
        
        # 更新对话状态
        self.db_service.update_conversation(conversation)

    def _format_conversation_history(self, conversation: Conversation) -> str:
        """格式化对话历史"""
        history = ""
        for msg in conversation.messages:
            role = "用户" if msg.role == "user" else "助手"
            history += f"{role}: {msg.content}\n\n"
        return history

    async def _check_goal_achieved(self, conversation: Conversation) -> bool:
        """检查对话目标是否达成"""
        conversation_history = self._format_conversation_history(conversation)
        prompt = self.goal_detection_prompt.format(conversation_history=conversation_history)
        result = await self.qwen_service.analyze_text(conversation_history, prompt)
        return "已解决" in result.get("raw_response", "")

    async def generate_summary(self, conversation: Conversation) -> str:
        """生成对话总结"""
        conversation_history = self._format_conversation_history(conversation)
        prompt = self.summary_prompt.format(conversation_history=conversation_history)
        result = await self.qwen_service.analyze_text(conversation_history, prompt)
        summary = result.get("raw_response", "总结生成失败")
        conversation.summary = summary
        self.db_service.update_conversation(conversation)
        return summary
        
    async def _analyze_user_intent(self, user_message: str) -> Dict[str, Any]:
        """分析用户意图
        
        Args:
            user_message: 用户消息
            
        Returns:
            Dict[str, Any]: 用户意图分析结果
        """
        # 构建提示模板
        intent_prompt = f"""请分析以下用户消息的意图，并返回JSON格式的结果。

用户消息: {user_message}

请分析以下内容:
1. 用户是否在询问酒店信息（如电话、地址等）
2. 用户是否提到了具体的酒店名称
3. 用户是否在请求换房
4. 用户是否在请求退款
5. 用户是否提供了订单号
6. 用户是否提供了房间号
7. 用户是否提供了更换原因

请以JSON格式返回结果，包含以下字段:
- is_asking_hotel_info
- hotel_name
- is_requesting_room_change
- is_requesting_refund
- order_number
- room_number
- change_reason

结果:"""
        
        try:
            # 使用千问API分析用户意图
            result = await self.qwen_service.analyze_text(user_message, intent_prompt)
            response = result.get("raw_response", "{}")
            
            # 尝试解析JSON结果
            import json
            try:
                # 尝试提取JSON部分
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                    intent_data = json.loads(json_str)
                else:
                    intent_data = json.loads(response)
                    
                return intent_data
            except json.JSONDecodeError as e:
                print(f"无法解析意图分析结果: {str(e)}")
                print(f"原始响应: {response}")
                
                # 使用简单的含关键词判断
                return {
                    "is_asking_hotel_info": "电话" in user_message or "地址" in user_message or "信息" in user_message,
                    "is_requesting_room_change": "换房" in user_message or "换一间" in user_message or "太吵" in user_message,
                    "is_requesting_refund": "退款" in user_message or "退钱" in user_message or "退订" in user_message
                }
        except Exception as e:
            print(f"分析用户意图时出错: {str(e)}")
            # 出错时返回空字典
            return {}
