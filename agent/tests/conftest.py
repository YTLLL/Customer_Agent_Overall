"""Pytest配置文件

这个文件包含了测试所需的fixture和配置。
"""

import os
import pytest
from dotenv import load_dotenv
from agent.app.models.conversation import Conversation, Message, ConversationStatus
from agent.app.agents.reasoning_agent import ReasoningAgent
from datetime import datetime

# 加载环境变量
load_dotenv()

@pytest.fixture
def test_conversation():
    """创建测试用的对话实例"""
    return Conversation(
        user_id="test_user_001",
        channel="web",
        status=ConversationStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        messages=[],
        metadata={},
        goal_achieved=False
    )

@pytest.fixture
def reasoning_agent():
    """创建推理代理实例"""
    return ReasoningAgent()

@pytest.fixture
def sample_messages():
    """创建测试用的消息列表"""
    return [
        Message(
            role="user",
            content="我想在喜来登酒店换一个房间，现在的房间太吵了",
            timestamp=datetime.now()
        ),
        Message(
            role="assistant",
            content="好的，我理解您的需求。为了帮您更换房间，请问您能告诉我您现在的房间号码吗？",
            timestamp=datetime.now()
        )
    ]