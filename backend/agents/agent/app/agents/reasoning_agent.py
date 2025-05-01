"""推理代理模块

这个模块实现了核心的推理代理功能，负责处理用户的酒店服务请求。
"""

import os
from typing import List, Dict, Any, Optional

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agent.app.models.conversation import Conversation, Message
from agent.app.utils.helpers import extract_hotel_name, format_hotel_info
from agent.app.services.qwen_text_service import QwenTextService

class ReasoningAgent:
    """推理代理类，负责处理用户的酒店服务请求"""
    
    def __init__(self):
        """初始化推理代理"""
        # 初始化通义千问文本理解服务
        self.qwen_service = QwenTextService()
        self._init_prompts()
    
    def _init_prompts(self):
        """初始化提示模板"""
        # 目标检测提示模板
        self._goal_detection_prompt = PromptTemplate(
            input_variables=["conversation_history"],
            template="""请分析以下对话历史，判断用户的问题是否已经得到解决：

{conversation_history}

如果用户的问题已经得到满意解决，请回复"已解决"；
如果问题仍未解决，请回复"未解决"。

回答："""
        )
        
        # 推理提示模板
        self.reasoning_prompt = PromptTemplate(
            input_variables=["conversation_history", "user_message", "hotel_info"],
            template="""你是一个专门帮助中老年人处理酒店服务问题的智能助手。
            你的任务是帮助用户解决酒店换房或退租的问题。
            请保持语言简洁、清晰，避免使用复杂术语。
            
            酒店信息：
            {hotel_info}
            
            对话历史：
            {conversation_history}
            
            用户问题：{user_message}
            
            请根据用户的问题和酒店信息提供帮助。如果你需要更多信息，请礼貌地询问。
            如果你认为问题已经解决，请明确告知用户并总结解决方案。
            
            请记住：
            1. 使用简单、直接的语言
            2. 提供明确的步骤和指导
            3. 如果需要用户联系酒店，提供具体的联系方式
            4. 避免使用技术术语或复杂的预订系统术语
            
            助手回复："""
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
            
            如果无法找到确切信息，请提供一个合理的模拟回答，以便能够继续对话。
            
            回答："""
        )
    
    async def process_request(self, conversation: Conversation, user_message: str) -> str:
        """处理用户请求并生成回复"""
        hotel_name = extract_hotel_name(user_message)
        hotel_info = await self._get_hotel_info(hotel_name)
        conversation_history = self._format_conversation_history(conversation)
        prompt = self.reasoning_prompt.format(conversation_history=conversation_history, user_message=user_message, hotel_info=hotel_info)
        result = await self.qwen_service.analyze_text(user_message, prompt)
        return result.get("raw_response", "对话生成失败")
    
    async def _get_hotel_info(self, hotel_name: str) -> str:
        if not hotel_name:
            return "未能识别酒店名称，请提供更多信息。"
        prompt = self.hotel_info_prompt.format(hotel_name=hotel_name)
        result = await self.qwen_service.analyze_text(hotel_name, prompt)
        return result.get("raw_response", "酒店信息获取失败")
    
    def _format_conversation_history(self, conversation: Conversation) -> str:
        """格式化对话历史"""
        history = ""
        for msg in conversation.messages:
            role = "用户" if msg.role == "user" else "助手"
            history += f"{role}: {msg.content}\n\n"
        return history
    
    async def check_goal_achieved(self, conversation: Conversation) -> bool:
        conversation_history = self._format_conversation_history(conversation)
        prompt = self._goal_detection_prompt.format(conversation_history=conversation_history)
        result = await self.qwen_service.analyze_text(conversation_history, prompt)
        return "已解决" in result.get("raw_response", "")