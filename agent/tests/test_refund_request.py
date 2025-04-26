"""退票请求测试模块

该模块测试退票请求的处理流程，包括信息提取、分析和prompt生成。
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agent.app.models.conversation import Conversation, Message
from agent.app.agents.reasoning_graph import ReasoningGraph, ReasoningState
from agent.app.agents.summary_agent import SummaryAgent
from agent.app.services.gaode_mcp_service import GaodeMCPService


@pytest.fixture
def conversation():
    """创建测试用的对话对象"""
    return Conversation(
        id="test_conversation",
        user_id="test_user",
        channel="test",
        messages=[
            Message(role="user", content="我想退票，酒店是北京希尔顿酒店，订单号是HT12345，入住日期是2025-05-01，客人是张三")
        ],
        metadata={}
    )


@pytest.fixture
def reasoning_graph():
    """创建推理图实例"""
    return ReasoningGraph()


@pytest.fixture
def summary_agent():
    """创建总结代理实例"""
    return SummaryAgent()


@pytest.mark.asyncio
async def test_analyze_refund_request(conversation, reasoning_graph):
    """测试分析退票请求功能"""
    # 准备测试数据
    user_message = "我想退票，酒店是北京希尔顿酒店，订单号是HT12345，入住日期是2025-05-01，客人是张三"
    
    # 创建初始状态
    initial_state = ReasoningState(
        conversation=conversation,
        user_message=user_message,
        hotel_name=None,
        hotel_info=None,
        response=None,
        goal_achieved=False,
        error=None,
        is_refund_request=True
    )
    
    # 模拟高德MCP服务的返回结果
    mock_result = {
        "is_complete": True,
        "extracted_info": {
            "hotel_name": "北京希尔顿酒店",
            "order_id": "HT12345",
            "check_in_date": "2025-05-01",
            "guest_name": "张三"
        },
        "missing_fields": [],
        "hotel_info": {
            "name": "北京希尔顿酒店",
            "formatted_address": "北京市东城区东长安街1号",
            "tel": "010-12345678",
            "policies": {
                "refund": "入住前24小时可免费取消"
            }
        }
    }
    
    # 模拟gaode_mcp_service.analyze_refund_request方法
    with patch('agent.app.services.gaode_mcp_service.gaode_mcp_service.analyze_refund_request', return_value=mock_result):
        # 调用被测试的方法
        updated_state = await reasoning_graph._analyze_refund_request(initial_state)
        
        # 验证结果
        assert updated_state["is_refund_complete"] == True
        assert len(updated_state["missing_fields"]) == 0
        assert "refund_info" in updated_state["conversation"].metadata
        
        # 验证refund_info中的字段
        refund_info = updated_state["conversation"].metadata["refund_info"]
        assert refund_info["hotel_name"] == "北京希尔顿酒店"
        assert refund_info["order_id"] == "HT12345"
        assert refund_info["check_in_date"] == "2025-05-01"
        assert refund_info["guest_name"] == "张三"
        
        # 验证酒店信息
        assert "hotel_info" in refund_info
        assert refund_info["hotel_info"]["tel"] == "010-12345678"
        assert "入住前24小时可免费取消" in refund_info["hotel_info"]["policies"]["refund"]


@pytest.mark.asyncio
async def test_analyze_refund_request_incomplete(conversation, reasoning_graph):
    """测试分析不完整的退票请求"""
    # 准备测试数据
    user_message = "我想退票，酒店是北京希尔顿酒店"
    
    # 创建初始状态
    initial_state = ReasoningState(
        conversation=conversation,
        user_message=user_message,
        hotel_name=None,
        hotel_info=None,
        response=None,
        goal_achieved=False,
        error=None,
        is_refund_request=True
    )
    
    # 模拟高德MCP服务的返回结果 - 信息不完整
    mock_result = {
        "is_complete": False,
        "extracted_info": {
            "hotel_name": "北京希尔顿酒店",
            "order_id": "缺失",
            "check_in_date": "缺失",
            "guest_name": "缺失"
        },
        "missing_fields": ["order_id", "check_in_date", "guest_name"],
        "hotel_info": {
            "name": "北京希尔顿酒店",
            "formatted_address": "北京市东城区东长安街1号",
            "tel": "010-12345678",
            "policies": {
                "refund": "入住前24小时可免费取消"
            }
        }
    }
    
    # 模拟gaode_mcp_service.analyze_refund_request方法
    with patch('agent.app.services.gaode_mcp_service.gaode_mcp_service.analyze_refund_request', return_value=mock_result):
        # 调用被测试的方法
        updated_state = await reasoning_graph._analyze_refund_request(initial_state)
        
        # 验证结果
        assert updated_state["is_refund_complete"] == False
        assert len(updated_state["missing_fields"]) == 3
        assert "missing_info_prompt" in updated_state
        assert "订单号" in updated_state["missing_info_prompt"]
        assert "入住日期" in updated_state["missing_info_prompt"]
        assert "客人姓名" in updated_state["missing_info_prompt"]
        
        # 验证refund_info中的字段
        refund_info = updated_state["conversation"].metadata["refund_info"]
        assert refund_info["hotel_name"] == "北京希尔顿酒店"
        assert "order_id" not in refund_info
        
        # 验证酒店信息
        assert "hotel_info" in refund_info


@pytest.mark.asyncio
async def test_generate_refund_prompt(conversation, summary_agent):
    """测试生成退票prompt"""
    # 准备测试数据 - 添加退票信息到conversation元数据
    conversation.metadata["refund_info"] = {
        "hotel_name": "北京希尔顿酒店",
        "order_id": "HT12345",
        "check_in_date": "2025-05-01",
        "guest_name": "张三",
        "hotel_info": {
            "name": "北京希尔顿酒店",
            "formatted_address": "北京市东城区东长安街1号",
            "tel": "010-12345678",
            "policies": {
                "refund": "入住前24小时可免费取消"
            }
        }
    }
    
    # 模拟QwenTextService.analyze_text方法
    mock_response = {
        "raw_response": "这是一个退票处理的prompt，包含了酒店信息、订单信息和退款政策。"
    }
    
    with patch('agent.app.services.qwen_text_service.QwenTextService.analyze_text', return_value=mock_response):
        # 调用被测试的方法
        refund_prompt = await summary_agent._generate_refund_prompt(conversation)
        
        # 验证结果
        assert refund_prompt is not None
        assert "退票处理" in refund_prompt


@pytest.mark.asyncio
async def test_process_refund_request(conversation, summary_agent):
    """测试处理退票请求并存储prompt"""
    # 准备测试数据 - 添加退票信息到conversation元数据
    conversation.metadata["refund_info"] = {
        "hotel_name": "北京希尔顿酒店",
        "order_id": "HT12345",
        "check_in_date": "2025-05-01",
        "guest_name": "张三",
        "hotel_info": {
            "name": "北京希尔顿酒店",
            "formatted_address": "北京市东城区东长安街1号",
            "tel": "010-12345678",
            "policies": {
                "refund": "入住前24小时可免费取消"
            }
        }
    }
    
    # 模拟QwenTextService.analyze_text方法
    mock_response = {
        "raw_response": "这是一个退票处理的prompt，包含了酒店信息、订单信息和退款政策。"
    }
    
    # 模拟DBService.save_conversation方法
    mock_save = MagicMock()
    
    with patch('agent.app.services.qwen_text_service.QwenTextService.analyze_text', return_value=mock_response), \
         patch.object(summary_agent.db_service, 'save_conversation', mock_save):
        # 调用被测试的方法
        result = await summary_agent.process_refund_request(conversation)
        
        # 验证结果
        assert result["success"] == True
        assert "refund_prompt" in result
        assert "退票处理" in result["refund_prompt"]
        
        # 验证保存到MongoDB的调用
        mock_save.assert_called_once_with(conversation)
        
        # 验证prompt已添加到元数据
        assert "refund_prompt" in conversation.metadata
        assert "退票处理" in conversation.metadata["refund_prompt"]


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])
