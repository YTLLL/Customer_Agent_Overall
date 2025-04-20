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
        # 准备对话历史
        conversation_history = self._format_conversation_history(conversation)
        # 生成回复
        prompt = self.conversation_prompt.format(conversation_history=conversation_history, user_message=user_message)
        result = await self.qwen_service.analyze_text(user_message, prompt)
        response = result.get("raw_response", "对话生成失败")
        assistant_message = Message(
            role="assistant",
            content=response.strip()
        )
        conversation.add_message(assistant_message)
        self.db_service.save_message(conversation.id, assistant_message)
        # 检查目标是否达成
        if len(conversation.messages) >= 4:
            goal_achieved = await self._check_goal_achieved(conversation)
            conversation.goal_achieved = goal_achieved
            if goal_achieved:
                conversation.status = ConversationStatus.COMPLETED
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