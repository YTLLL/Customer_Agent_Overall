
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

from agent.app.agents.summary_agent import SummaryAgent  # 引入 SummaryAgent
class CallingAgentService:
    """代理服务类，负责处理用户请求和生成回复"""

    def __init__(self):
        """初始化代理服务"""
        # 初始化数据库服务
        self.db_service = DBService()
        self.refund_prompt = ""
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
        self.goal_detection_prompt = """请分析以下退票相关对话，判断退票流程是否已经完成。

    对话历史：
    {conversation_history}

    请仔细分析对话内容，判断是否满足以下所有条件：
    1. 酒店已确认收到退票申请
    2. 退款金额已经确定
    3. 退款时间或处理期限已明确
    4. 双方对退款条件达成一致
    5. 没有遗留的重要问题需要解决

    如果以上条件全部满足，请回复"已解决"；如果还有未完成的步骤，请回复"未解决"并说明原因。

    分析结果："""

    def get_refund_prompt(self, user_id: str) -> str:
        """
        获取用户的退票提示

        Args:
            user_id: 用户ID

        Returns:
            str: 退票提示内容

        Raises:
            HTTPException: 当找不到退票提示时抛出404错误
        """
        # 获取用户最近的活跃对话
        # conversation = self.db_service.get_active_conversation(user_id)
        #
        # if not conversation:
        #     raise HTTPException(
        #         status_code=404,
        #         detail="未找到活跃的对话"
        #     )
        #
        # # 从对话元数据中获取退票提示
        # refund_prompt = conversation.metadata.get("refund_prompt")
        self.refund_prompt = "很好，很感谢你"

        if not self.refund_prompt:
            raise HTTPException(
                status_code=404,
                detail="hou未找到退票提示信息"
            )

        return self.refund_prompt

    async def process_message(self, conversation_id: str, message: str) -> None:
        """
        处理与酒店的沟通消息，根据退票提示生成回复并更新对话状态

        Args:
            conversation_id: 对话ID
            message: 酒店方的消息文本
        """
        # 获取对话
        conversation = self.db_service.get_conversation(conversation_id)
        if not conversation:
            return

        # 检查对话是否已超过最大轮次
        if len(conversation.messages) >= self.max_turns * 2:
            final_message = Message(
                role="assistant",
                content="很抱歉，我们的对话已经进行了较长时间。为了更好地解决您的问题，建议您联系酒店其他渠道继续处理。感谢您的理解。"
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

        try:
            # 获取退票提示
            refund_prompt = "你好"
            if not refund_prompt:
                raise ValueError("未找到退票提示信息")

            # 准备对话历史
            conversation_history = self._format_conversation_history(conversation)

            # 构建提示模板
            prompt_template = f"""
            你是一位专业的用户客服代表，正在代表用户向酒店处理退票事宜。

            退票相关信息：
            {refund_prompt}

            对话历史：
            {conversation_history}

            酒店方最新消息：
            {message}

            请根据以上信息，生成专业、礼貌且符合实际情况的回复。回复需要：
            1. 准确回应酒店方的具体问题或要求
            2. 确保信息与退票提示中的细节保持一致
            3. 推进退票流程的顺利进行
            4. 保持专业和礼貌的沟通语气

            回复：
            """

            # 生成回复
            response = await self.qwen_service.analyze_text(conversation_history, prompt_template)
            if isinstance(response, dict) and "raw_response" in response:
                response_text = response["raw_response"]
            else:
                response_text = str(response)
            # 创建并保存助手消息
            assistant_message = Message(
                role="assistant",
                content=response_text
            )
            conversation.add_message(assistant_message)
            self.db_service.save_message(conversation.id, assistant_message)

            # 检查目标是否达成
            if len(conversation.messages) >= 4:
                goal_achieved = await self._check_goal_achieved(conversation)
                conversation.goal_achieved = goal_achieved
                if goal_achieved:
                    conversation.status = ConversationStatus.COMPLETED

            # 更新对话状态
            self.db_service.update_conversation(conversation)

        except Exception as e:
            error_message = Message(
                role="assistant",
                content=f"处理消息时出错: {str(e)}"
            )
            conversation.add_message(error_message)
            self.db_service.save_message(conversation.id, error_message)
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
    def check_summary(self, conversation:Conversation):
        # get summary from summary agent
        summary_agent = SummaryAgent()
        summary = summary_agent.generate_calling_summary(conversation)
        conversation.metadata["summary"] = summary
        return summary
    def save_conversation(self):
        # save conversation to db
        pass