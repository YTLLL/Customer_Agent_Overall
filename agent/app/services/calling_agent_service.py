
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
from agent.app.services.calling_db_service import CallingDBService
from agent.app.services.qwen_text_service import QwenTextService

from agent.app.agents.summary_agent import SummaryAgent  # 引入 SummaryAgent
class CallingAgentService:
    """代理服务类，负责处理用户请求和生成回复"""

    def __init__(self):
        self.first_time = True
        """初始化代理服务"""
        # 初始化数据库服务
        self.user_id = None
        self.db_service = CallingDBService()
        self.refund_prompt = ""
        # 初始化通义千问文本理解服务
        self.qwen_service = QwenTextService()
        # 设置最大对话轮次
        self.max_turns = int(os.getenv("MAX_CONVERSATION_TURNS", "30"))
        # 设置对话超时时间（小时）
        self.timeout_hours = int(os.getenv("CONVERSATION_TIMEOUT_HOURS", "6"))
        # 初始化提示模板
        self._init_prompts()

    def _init_prompts(self):
        """初始化提示模板"""
        self.goal_detection_prompt = """你是一个对话理解助手。请根据以下对话内容，判断用户的问题是否已经被成功解决。  
对话双方是第三方（客户、用户）和通话代理（客服、助手）。

请遵循以下要求：
- 如果问题已经完全解决，返回 True
- 如果问题仍未解决，返回 False
- 只返回单个单词 True 或 False，不要添加任何其他解释或文字

对话内容：
{conversation}

你的回答"""
        self.chat_prompt = """你正在与第三方平台进行沟通。

以下是你与第三方的聊天记录，请根据这些内容，继续用专业、礼貌的口吻向第三方表达用户的诉求。

要求：
- 你是在和第三方直接说话，请根据已有聊天内容生成你要对第三方说的话
- 不要复述聊天记录，不要重复已经说过的话
- 只生成需要继续沟通或总结表达的内容
- 语气正式且友好，内容清晰简洁，方便第三方理解与处理
- 如有必要，可以适当补充背景信息，但不能编造不存在的信息

聊天记录：
{conversation_history}

请生成你对第三方说的话：

"""

    def get_prompt(self, user_id: str) -> str:
        """
        获取用户的退票提示

        Args:
            user_id: 用户ID

        Returns:
            str: 退票提示内容
        """
        refund_prompt_collection = self.db_service.reasoning_db['refund_prompts']
        refund_prompt = refund_prompt_collection.find_one(
            {"user_id": user_id},  # 查询条件
            sort=[("_id", -1)]  # 按 _id 倒序（_id天生自带时间戳，越新的_id越大）
        )["prompt"]

        print("found refund prompt", refund_prompt)

        if not refund_prompt:
            print("未找到退票信息")

        return refund_prompt

    async def process_message(self, conversation_id: str, message: str, user_id: str) -> Optional[str]:
        """
        Process communication messages with hotels, generate responses based on refund prompts
        and update conversation status.

        Args:
            conversation_id (str): The conversation ID
            message (str): Message text from the third party
            user_id (str): The user's ID

        Returns:
            Optional[str]: The content of the response message to be sent to the frontend
        """
        # Get conversation
        print("process_message")
        conversation = self.db_service.get_conversation(conversation_id)
        if len(conversation.messages) >= 2:
            goal_achieved = await self._check_goal_achieved(conversation)
            conversation.goal_achieved = goal_achieved
            if goal_achieved:
                final_content = "感谢您的帮助和处理。问题已经解决，如后续还有其他情况我们会及时联系。再次感谢！"
                final_message = Message(
                    role="assistant",
                    content=final_content
                )
                conversation.add_message(final_message)
                self.db_service.save_message(conversation.id, final_message)
                conversation.status = ConversationStatus.COMPLETED
                self.db_service.update_conversation(conversation)
                return final_content
        print("conversation is ", conversation)
        if not conversation:
            return None

        # First add the received message to conversation
        received_message = Message(
            role="user",  # Assuming third party messages are treated as user messages
            content=message
        )
        conversation.add_message(received_message)
        self.db_service.save_message(conversation.id, received_message)
        print("still alive")
        # Check goal achievement using goal detection prompt
        conversation_history = self._format_conversation_history(conversation)

        goal_detection_response = await self.qwen_service.analyze_text(
            conversation_history,
            self.goal_detection_prompt.format(conversation=conversation_history)
        )
        print("goal detection is ", goal_detection_response)

        if isinstance(goal_detection_response, dict):
            goal_achieved = goal_detection_response.get("raw_response", "").strip().lower() == "true"
        else:
            goal_achieved = str(goal_detection_response).strip().lower() == "true"

        if goal_achieved:
            final_content = "感谢您的帮助和处理。问题已经解决，如后续还有其他情况我们会及时联系。再次感谢！"
            final_message = Message(
                role="assistant",
                content=final_content
            )
            conversation.add_message(final_message)
            self.db_service.save_message(conversation.id, final_message)
            conversation.status = ConversationStatus.COMPLETED
            conversation.goal_achieved = True
            self.db_service.update_conversation(conversation)
            await self.check_summary(conversation)
            return final_content
        print("goal achieved")
        # Check if conversation has exceeded maximum turns
        if len(conversation.messages) >= self.max_turns * 2:
            final_content = "抱歉占用了您这么多时间。由于问题可能需要进一步核实，我们稍后会通过其他渠道继续跟进。感谢您的耐心帮助。"
            final_message = Message(
                role="assistant",
                content=final_content
            )
            conversation.add_message(final_message)
            self.db_service.save_message(conversation.id, final_message)
            conversation.status = ConversationStatus.COMPLETED
            self.db_service.update_conversation(conversation)
            return final_content

        # Check for conversation timeout
        if conversation.is_timeout(self.timeout_hours):
            conversation.status = ConversationStatus.TIMEOUT
            self.db_service.update_conversation(conversation)
            return None

        try:
            # Get refund prompt
            refund_prompt = self.get_prompt(user_id)
            if not refund_prompt:
                raise ValueError("未找到退票提示信息")

            # Prepare conversation history
            conversation_history = self._format_conversation_history(conversation)
            print("conversation history")
            # Build prompt template
            if self.first_time:
                prompt_template = refund_prompt + self.chat_prompt
                self.first_time = False
            else:
                prompt_template = self.chat_prompt

            # Generate response
            response = await self.qwen_service.analyze_text(conversation_history, prompt_template)
            response_text = response["raw_response"] if isinstance(response,
                                                                   dict) and "raw_response" in response else str(
                response)
            print("response_text ", response_text)
            # Create and save assistant message
            assistant_message = Message(
                role="assistant",
                content=response_text
            )
            conversation.add_message(assistant_message)
            print("add _message)")
            self.db_service.save_message(conversation.id, assistant_message)
            return response_text
            # Check if goal is achieved


            # Update conversation status
            self.db_service.update_conversation(conversation)

        except Exception as e:
            error_content = f"处理消息时出错: {str(e)}"
            error_message = Message(
                role="assistant",
                content=error_content
            )
            conversation.add_message(error_message)
            self.db_service.save_message(conversation.id, error_message)
            self.db_service.update_conversation(conversation)
            return error_content
            #     async def process_message(self, conversation_id: str, message: str, user_id: str) -> None:
#         """
#         处理与酒店的沟通消息，根据退票提示生成回复并更新对话状态
#
#         Args:
#             conversation_id: 对话ID
#             message: 酒店方的消息文本
#         """
#         # 获取对话
#         conversation = self.db_service.get_conversation(conversation_id)
#         if not conversation:
#             return
#
#         # 检查对话是否已超过最大轮次
#         if len(conversation.messages) >= self.max_turns * 2:
#             final_message = Message(
#                 role="assistant",
#                 content="很抱歉，我们的对话已经进行了较长时间。为了更好地解决您的问题，建议您联系酒店其他渠道继续处理。感谢您的理解。"
#             )
#             conversation.add_message(final_message)
#             self.db_service.save_message(conversation.id, final_message)
#             conversation.status = ConversationStatus.COMPLETED
#             self.db_service.update_conversation(conversation)
#             return
#
#         # 检查对话是否超时
#         if conversation.is_timeout(self.timeout_hours):
#             conversation.status = ConversationStatus.TIMEOUT
#             self.db_service.update_conversation(conversation)
#             return
#
#         try:
#             # 获取退票提示
#             refund_prompt = self.get_refund_prompt(user_id)
#             if not refund_prompt:
#                 raise ValueError("未找到退票提示信息")
#
#             # 准备对话历史
#             conversation_history = self._format_conversation_history(conversation)
#
#             # 构建提示模板
#             prompt_template = """以下是用户与通话代理的对话记录，请结合用户信息、客户诉求和对话内容，生成一段专业、礼貌的文本，用于向第三方平台转达用户的请求。
#
# 要求：
# - 保持语气正式且友好
# - 明确表达用户的核心诉求
# - 如有必要，可适当补充背景信息，但不要编造不存在的内容
# - 不要提及对话代理或中间处理过程，只以用户的立场发言
# - 语言简洁流畅，便于第三方快速理解和处理
#
# 对话记录：
# {conversation_history}
#
# 请生成发送给第三方平台的文本："""
#
#             # 生成回复
#             response = await self.qwen_service.analyze_text(conversation_history, prompt_template)
#             if isinstance(response, dict) and "raw_response" in response:
#                 response_text = response["raw_response"]
#             else:
#                 response_text = str(response)
#             # 创建并保存助手消息
#             assistant_message = Message(
#                 role="assistant",
#                 content=response_text
#             )
#             conversation.add_message(assistant_message)
#             self.db_service.save_message(conversation.id, assistant_message)
#
#             # 检查目标是否达成
#             if len(conversation.messages) >= 4:
#                 goal_achieved = await self._check_goal_achieved(conversation)
#                 conversation.goal_achieved = goal_achieved
#                 if goal_achieved:
#                     conversation.status = ConversationStatus.COMPLETED
#
#             # 更新对话状态
#             self.db_service.update_conversation(conversation)
#
#         except Exception as e:
#             error_message = Message(
#                 role="assistant",
#                 content=f"处理消息时出错: {str(e)}"
#             )
#             conversation.add_message(error_message)
#             self.db_service.save_message(conversation.id, error_message)
#             self.db_service.update_conversation(conversation)

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
        prompt = self.goal_detection_prompt.format(conversation=conversation_history)
        result = await self.qwen_service.analyze_text(conversation_history, prompt)
        return "true" == result.get("raw_response", "").lower()
    def check_summary(self, conversation:Conversation):
        # get summary from summary agent
        summary_agent = SummaryAgent()
        summary = summary_agent.generate_calling_summary(conversation)
        conversation.metadata["summary"] = summary
        return summary
    def save_conversation(self):
        # save conversation to db
        pass