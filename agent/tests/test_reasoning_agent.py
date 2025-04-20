"""推理代理模块的单元测试

测试ReasoningAgent类的核心功能和异常处理。
"""

import pytest
from datetime import datetime
from agent.app.models.conversation import Message

@pytest.mark.asyncio
async def test_process_request(test_conversation, reasoning_agent):
    """测试处理用户请求的功能"""
    # 准备测试数据
    user_message = "我想在喜来登酒店换一个房间，现在的房间太吵了"
    
    # 执行请求处理
    response = await reasoning_agent.process_request(test_conversation, user_message)
    
    # 验证响应
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    assert "房间" in response or "酒店" in response

@pytest.mark.asyncio
async def test_get_hotel_info(reasoning_agent):
    """测试获取酒店信息的功能"""
    # 测试有效酒店名称
    hotel_info = await reasoning_agent._get_hotel_info("喜来登")
    assert hotel_info is not None
    assert isinstance(hotel_info, str)
    assert len(hotel_info) > 0
    assert "喜来登" in hotel_info
    
    # 测试无效酒店名称
    hotel_info = await reasoning_agent._get_hotel_info("")
    assert "未能识别酒店名称" in hotel_info

def test_format_conversation_history(test_conversation, reasoning_agent, sample_messages):
    """测试对话历史格式化功能"""
    # 添加测试消息
    test_conversation.messages.extend(sample_messages)
    
    # 获取格式化的对话历史
    history = reasoning_agent._format_conversation_history(test_conversation)
    
    # 验证格式化结果
    assert history is not None
    assert isinstance(history, str)
    assert "用户:" in history
    assert "助手:" in history
    assert "喜来登酒店" in history

@pytest.mark.asyncio
async def test_check_goal_achieved(test_conversation, reasoning_agent, sample_messages):
    """测试目标完成检查功能"""
    # 添加测试消息
    test_conversation.messages.extend(sample_messages)
    
    # 添加完成对话的消息
    test_conversation.messages.append(
        Message(
            role="user",
            content="好的，我知道了，谢谢你的帮助",
            timestamp=datetime.now()
        )
    )
    
    # 检查目标是否完成
    goal_achieved = await reasoning_agent.check_goal_achieved(test_conversation)
    assert isinstance(goal_achieved, bool)