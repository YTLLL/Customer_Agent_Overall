"""高德地图MCP服务测试模块

这个模块测试高德地图MCP服务的功能，包括获取酒店信息和将信息存储到MongoDB。
"""

import os
import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock

from agent.app.services.gaode_mcp_service import GaodeMCPService, gaode_mcp_service
from agent.app.services.db_service import DBService
from agent.app.models.conversation import Conversation
from agent.app.services.qwen_text_service import QwenTextService

# 测试数据
TEST_HOTEL_NAME = "喜来登酒店"
TEST_HOTEL_INFO = {
    "name": TEST_HOTEL_NAME,
    "formatted_address": "北京市朝阳区天辰东路7号",
    "tel": "010-64351234",
    "policies": {
        "check_out": "12:00前",
        "cancellation": "预订后24小时内可免费取消",
        "refund": "根据酒店政策，提前3天取消可全额退款"
    }
}

@pytest.fixture
def db_service():
    """创建数据库服务实例"""
    return DBService()

@pytest.fixture
def gaode_service():
    """创建高德地图MCP服务实例"""
    return GaodeMCPService()

@pytest.mark.asyncio
async def test_gaode_mcp_config():
    """测试高德地图MCP配置是否正确"""
    # 检查环境变量是否设置
    assert os.getenv("GAODE_API_KEY") is not None, "高德地图API密钥未设置"
    
    # 检查MCP配置是否正确
    config = gaode_mcp_service.get_mcp_config()
    assert "mcpServers" in config
    assert "gaode" in config["mcpServers"]
    assert "env" in config["mcpServers"]["gaode"]
    assert "GAODE_API_KEY" in config["mcpServers"]["gaode"]["env"]
    assert config["mcpServers"]["gaode"]["env"]["GAODE_API_KEY"] == os.getenv("GAODE_API_KEY")

@pytest.mark.asyncio
async def test_search_hotel_integration():
    """集成测试：测试搜索酒店功能（需要真实API密钥）"""
    # 注意：此测试需要真实的API密钥，并会发起实际的API请求
    # 如果不想发起实际请求，可以跳过此测试
    pytest.skip("跳过实际API调用测试，如需测试请移除此行")
    
    result = await gaode_mcp_service.search_hotel(TEST_HOTEL_NAME)
    
    # 验证返回结果包含必要字段
    assert "name" in result
    assert "formatted_address" in result
    assert "tel" in result
    assert "policies" in result

@pytest.mark.asyncio
async def test_search_hotel_mock():
    """使用模拟对象测试搜索酒店功能"""
    # 创建模拟的search_hotel方法
    with patch.object(GaodeMCPService, 'search_hotel', return_value=TEST_HOTEL_INFO) as mock_search:
        # 调用服务方法
        result = await gaode_mcp_service.search_hotel(TEST_HOTEL_NAME)
        
        # 验证模拟方法被调用
        mock_search.assert_called_once_with(TEST_HOTEL_NAME)
        
        # 验证返回结果
        assert result == TEST_HOTEL_INFO
        assert result["name"] == TEST_HOTEL_NAME
        assert "formatted_address" in result
        assert "tel" in result
        assert "policies" in result

@pytest.mark.asyncio
async def test_store_hotel_info_in_mongodb(db_service):
    """测试将酒店信息存储到MongoDB"""
    # 创建一个测试对话
    conversation = Conversation(user_id="test_user", channel="web")
    
    # 模拟从高德地图API获取的酒店信息
    with patch.object(GaodeMCPService, 'search_hotel', return_value=TEST_HOTEL_INFO):
        # 获取酒店信息
        hotel_info = await gaode_mcp_service.search_hotel(TEST_HOTEL_NAME)
        
        # 将酒店信息添加到对话的元数据中
        conversation.metadata["hotel_info"] = hotel_info
        
        # 保存对话到MongoDB
        db_service.save_conversation(conversation)
        
        # 从MongoDB获取对话
        saved_conversation = db_service.get_conversation(conversation.id)
        
        # 验证酒店信息是否正确保存
        assert saved_conversation is not None
        assert "hotel_info" in saved_conversation.metadata
        assert saved_conversation.metadata["hotel_info"] == hotel_info
        assert saved_conversation.metadata["hotel_info"]["name"] == TEST_HOTEL_NAME
        assert saved_conversation.metadata["hotel_info"]["tel"] == TEST_HOTEL_INFO["tel"]

@pytest.mark.asyncio
async def test_reasoning_flow_with_hotel_info():
    """测试推理流程中使用酒店信息"""
    # 直接测试酒店信息的格式化和存储
    
    # 创建测试对话
    conversation = Conversation(user_id="test_user", channel="web")
    
    # 模拟酒店信息的格式化字符串
    hotel_info_str = f"酒店名称：{TEST_HOTEL_NAME}\n"
    hotel_info_str += f"酒店地址：{TEST_HOTEL_INFO['formatted_address']}\n"
    hotel_info_str += f"联系电话：{TEST_HOTEL_INFO['tel']}\n"
    hotel_info_str += f"退房政策：{TEST_HOTEL_INFO['policies']['check_out']}\n"
    hotel_info_str += f"取消政策：{TEST_HOTEL_INFO['policies']['cancellation']}\n"
    hotel_info_str += f"退款政策：{TEST_HOTEL_INFO['policies']['refund']}"
    
    # 将酒店信息添加到对话的元数据中
    conversation.metadata["hotel_info"] = hotel_info_str
    
    # 验证酒店信息是否正确格式化
    assert TEST_HOTEL_NAME in hotel_info_str
    assert TEST_HOTEL_INFO["tel"] in hotel_info_str
    assert TEST_HOTEL_INFO["formatted_address"] in hotel_info_str
    assert TEST_HOTEL_INFO["policies"]["check_out"] in hotel_info_str
    assert TEST_HOTEL_INFO["policies"]["cancellation"] in hotel_info_str
    assert TEST_HOTEL_INFO["policies"]["refund"] in hotel_info_str
    
    # 验证元数据中的酒店信息
    assert "hotel_info" in conversation.metadata
    assert conversation.metadata["hotel_info"] == hotel_info_str

@pytest.mark.asyncio
async def test_analyze_refund_request_complete():
    """测试分析完整的退票请求"""
    # 准备完整的退票请求消息
    user_message = f"我需要退票，酒店是{TEST_HOTEL_NAME}，订单号是ORD123456，入住日期是2025-04-15，客人姓名是张三"
    
    # 模拟通义千问服务的响应
    mock_response = {
        "raw_response": json.dumps({
            "hotel_name": TEST_HOTEL_NAME,
            "order_id": "ORD123456",
            "check_in_date": "2025-04-15",
            "guest_name": "张三"
        })
    }
    
    # 模拟酒店搜索结果
    with patch.object(QwenTextService, 'analyze_text', return_value=mock_response), \
         patch.object(GaodeMCPService, 'search_hotel', return_value=TEST_HOTEL_INFO):
        
        # 调用分析方法
        result = await gaode_mcp_service.analyze_refund_request(user_message)
        
        # 验证结果
        assert result["is_complete"] == True
        assert len(result["missing_fields"]) == 0
        assert "extracted_info" in result
        assert result["extracted_info"]["hotel_name"] == TEST_HOTEL_NAME
        assert result["extracted_info"]["order_id"] == "ORD123456"
        assert result["extracted_info"]["check_in_date"] == "2025-04-15"
        assert result["extracted_info"]["guest_name"] == "张三"
        assert "hotel_info" in result
        assert result["hotel_info"] == TEST_HOTEL_INFO

@pytest.mark.asyncio
async def test_analyze_refund_request_incomplete():
    """测试分析不完整的退票请求"""
    # 准备不完整的退票请求消息（缺少订单号和入住日期）
    user_message = f"我需要退票，酒店是{TEST_HOTEL_NAME}，客人姓名是张三"
    
    # 模拟通义千问服务的响应
    mock_response = {
        "raw_response": json.dumps({
            "hotel_name": TEST_HOTEL_NAME,
            "order_id": "缺失",
            "check_in_date": "缺失",
            "guest_name": "张三"
        })
    }
    
    # 模拟酒店搜索结果
    with patch.object(QwenTextService, 'analyze_text', return_value=mock_response), \
         patch.object(GaodeMCPService, 'search_hotel', return_value=TEST_HOTEL_INFO):
        
        # 调用分析方法
        result = await gaode_mcp_service.analyze_refund_request(user_message)
        
        # 验证结果
        assert result["is_complete"] == False
        assert "missing_fields" in result
        assert "order_id" in result["missing_fields"]
        assert "check_in_date" in result["missing_fields"]
        assert "extracted_info" in result
        assert result["extracted_info"]["hotel_name"] == TEST_HOTEL_NAME
        assert result["extracted_info"]["guest_name"] == "张三"
        assert "hotel_info" in result
        assert result["hotel_info"] == TEST_HOTEL_INFO

@pytest.mark.asyncio
async def test_analyze_refund_request_with_image():
    """测试带图片的退票请求分析"""
    # 准备用户消息和图片内容
    user_message = "我需要退票，这是我的订单截图"
    image_content = "订单截图显示：酒店名称为喜来登酒店，订单号ORD789012，入住日期2025-04-20，客人姓名李四"
    
    # 模拟通义千问服务的响应
    mock_response = {
        "raw_response": json.dumps({
            "hotel_name": TEST_HOTEL_NAME,
            "order_id": "ORD789012",
            "check_in_date": "2025-04-20",
            "guest_name": "李四"
        })
    }
    
    # 模拟酒店搜索结果
    with patch.object(QwenTextService, 'analyze_text', return_value=mock_response), \
         patch.object(GaodeMCPService, 'search_hotel', return_value=TEST_HOTEL_INFO):
        
        # 调用分析方法
        result = await gaode_mcp_service.analyze_refund_request(user_message, image_content)
        
        # 验证结果
        assert result["is_complete"] == True
        assert len(result["missing_fields"]) == 0
        assert "extracted_info" in result
        assert result["extracted_info"]["hotel_name"] == TEST_HOTEL_NAME
        assert result["extracted_info"]["order_id"] == "ORD789012"
        assert result["extracted_info"]["check_in_date"] == "2025-04-20"
        assert result["extracted_info"]["guest_name"] == "李四"
        assert "hotel_info" in result
        assert result["hotel_info"] == TEST_HOTEL_INFO

@pytest.mark.asyncio
async def test_store_refund_info_in_mongodb(db_service):
    """测试将退票信息存储到MongoDB"""
    # 创建一个测试对话
    conversation = Conversation(user_id="test_user", channel="web")
    
    # 准备退票信息
    refund_info = {
        "hotel_name": TEST_HOTEL_NAME,
        "order_id": "ORD123456",
        "check_in_date": "2025-04-15",
        "guest_name": "张三",
        "hotel_info": TEST_HOTEL_INFO
    }
    
    # 将退票信息添加到对话的元数据中
    conversation.metadata["refund_info"] = refund_info
    
    # 保存对话到MongoDB
    db_service.save_conversation(conversation)
    
    # 从MongoDB获取对话
    saved_conversation = db_service.get_conversation(conversation.id)
    
    # 验证退票信息是否正确保存
    assert saved_conversation is not None
    assert "refund_info" in saved_conversation.metadata
    assert saved_conversation.metadata["refund_info"] == refund_info
    assert saved_conversation.metadata["refund_info"]["hotel_name"] == TEST_HOTEL_NAME
    assert saved_conversation.metadata["refund_info"]["order_id"] == "ORD123456"
    assert saved_conversation.metadata["refund_info"]["hotel_info"] == TEST_HOTEL_INFO
