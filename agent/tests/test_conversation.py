"""对话模型的单元测试

测试Conversation和Message模型的功能。
"""

import pytest
from datetime import datetime, timedelta
from agent.app.models.conversation import Conversation, Message, ConversationStatus

def test_conversation_creation(test_conversation):
    """测试对话创建功能"""
    assert test_conversation.user_id == "test_user_001"
    assert test_conversation.channel == "web"
    assert test_conversation.status == ConversationStatus.ACTIVE
    assert isinstance(test_conversation.created_at, datetime)
    assert isinstance(test_conversation.updated_at, datetime)
    assert len(test_conversation.messages) == 0
    assert isinstance(test_conversation.metadata, dict)
    assert test_conversation.goal_achieved is False

def test_message_creation():
    """测试消息创建功能"""
    timestamp = datetime.now()
    message = Message(
        role="user",
        content="测试消息内容",
        timestamp=timestamp
    )
    
    assert message.role == "user"
    assert message.content == "测试消息内容"
    assert message.timestamp == timestamp

def test_conversation_add_message(test_conversation):
    """测试添加消息到对话"""
    message = Message(
        role="user",
        content="测试消息内容",
        timestamp=datetime.now()
    )
    
    # 添加消息
    test_conversation.messages.append(message)
    
    assert len(test_conversation.messages) == 1
    assert test_conversation.messages[0].content == "测试消息内容"

def test_conversation_status_update(test_conversation):
    """测试对话状态更新"""
    # 更新状态
    test_conversation.status = ConversationStatus.COMPLETED
    
    assert test_conversation.status == ConversationStatus.COMPLETED

def test_conversation_metadata(test_conversation):
    """测试对话元数据操作"""
    # 添加元数据
    test_conversation.metadata["room_number"] = "1204"
    test_conversation.metadata["hotel_name"] = "喜来登"
    
    assert test_conversation.metadata["room_number"] == "1204"
    assert test_conversation.metadata["hotel_name"] == "喜来登"

def test_conversation_goal_achievement(test_conversation):
    """测试目标完成状态更新"""
    # 更新目标完成状态
    test_conversation.goal_achieved = True
    
    assert test_conversation.goal_achieved is True