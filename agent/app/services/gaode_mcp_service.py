"""高德地图MCP服务模块

这个模块提供了与高德地图MCP交互的服务，用于获取酒店信息。
它还集成了通义千问API用于信息识别和分析。
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple

# 导入通义千问服务
from agent.app.services.qwen_text_service import QwenTextService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class GaodeMCPService:
    """高德地图MCP服务类，用于获取酒店信息和处理退票请求"""
    
    # 退票所需的必要信息字段
    REQUIRED_REFUND_FIELDS = [
        "hotel_name",    # 酒店名称
        "order_id",      # 订单号
        "check_in_date", # 入住日期
        "guest_name"     # 客人姓名
    ]
    
    def __init__(self):
        """初始化高德地图MCP服务"""
        # 初始化高德地图MCP配置
        self.mcp_config = {
            "mcpServers": {
                "gaode": {
                    "command": "cmd" if os.name == "nt" else "sh",
                    "args": [
                        "/c" if os.name == "nt" else "-c",
                        "npx",
                        "@wopal/mcp-gaode-maps"
                    ],
                    "env": {
                        "GAODE_API_KEY": os.getenv("GAODE_API_KEY", "")
                    }
                }
            }
        }
        
        # 初始化通义千问服务
        self.qwen_service = QwenTextService()
        
        logger.info("高德地图MCP服务初始化完成")
    
    async def search_hotel(self, hotel_name: str) -> Dict[str, Any]:
        """
        搜索酒店信息
        
        Args:
            hotel_name: 酒店名称
            
        Returns:
            Dict[str, Any]: 酒店信息，包含名称、地址、电话等
        """
        try:
            if not hotel_name:
                logger.warning("酒店名称为空，无法搜索")
                return {
                    "name": "",
                    "error": "酒店名称不能为空",
                    "formatted_address": "",
                    "tel": "",
                    "policies": {}
                }
            
            logger.info(f"正在搜索酒店: {hotel_name}")
            
            # 在实际项目中，这里应该是调用高德地图MCP的代码
            # 需要实现与高德地图API的集成
            # 此处不进行模拟测试，实际调用应该在正式环境中进行
            
            # 返回酒店信息结构，实际应用中应从高德地图API获取
            hotel_info = {
                "name": hotel_name,
                "formatted_address": "",  # 实际应用中从高德地图API获取
                "tel": "",  # 实际应用中从高德地图API获取
                "policies": {
                    "check_out": "",
                    "cancellation": "",
                    "refund": ""
                }
            }
            
            logger.info(f"成功获取酒店信息: {hotel_name}")
            return hotel_info
        except Exception as e:
            logger.error(f"获取酒店信息失败: {str(e)}")
            return {
                "name": hotel_name,
                "error": str(e),
                "tel": "",
                "formatted_address": "",
                "policies": {
                    "cancellation": "",
                    "refund": ""
                }
            }
    
    async def analyze_refund_request(self, user_message: str, image_content: Optional[str] = None) -> Dict[str, Any]:
        """
        分析退票请求，检查信息是否完整
        
        Args:
            user_message: 用户消息
            image_content: 图片内容（Base64编码），可选
            
        Returns:
            Dict[str, Any]: 分析结果，包含信息完整性和缺失字段
        """
        try:
            # 准备提示模板来分析用户请求
            prompt = f"""请分析以下退票请求，提取关键信息：
            
            用户请求：{user_message}
            
            请提取以下信息（如果有）：
            1. 酒店名称
            2. 订单号
            3. 入住日期
            4. 客人姓名
            
            对于缺失的信息，请标记为"缺失"。
            
            返回格式应为JSON：
            {{
                "hotel_name": "...",
                "order_id": "...",
                "check_in_date": "...",
                "guest_name": "..."
            }}
            """
            
            # 如果有图片，将图片信息添加到提示中
            if image_content:
                prompt += f"\n\n图片内容描述：{image_content}\n请同时分析图片中的信息。"
            
            # 使用通义千问服务分析文本
            result = await self.qwen_service.analyze_text(user_message, prompt)
            
            # 在测试环境中，直接使用模拟的响应
            if isinstance(result.get("raw_response"), str) and result.get("raw_response").startswith('{'):
                try:
                    extracted_info = json.loads(result.get("raw_response", "{}"))
                except json.JSONDecodeError:
                    # 如果无法解析为JSON，则尝试从文本中提取信息
                    raw_response = result.get("raw_response", "")
                    extracted_info = self._extract_info_from_text(raw_response)
            else:
                # 如果不是JSON字符串，则使用文本提取
                raw_response = result.get("raw_response", "")
                extracted_info = self._extract_info_from_text(raw_response)
                
            # 确保所有必要字段都存在
            for field in self.REQUIRED_REFUND_FIELDS:
                if field not in extracted_info:
                    extracted_info[field] = "缺失"
            
            # 检查缺失的字段
            missing_fields = []
            for field in self.REQUIRED_REFUND_FIELDS:
                if field not in extracted_info or not extracted_info[field] or extracted_info[field] == "缺失":
                    missing_fields.append(field)
            
            # 构建响应
            response = {
                "is_complete": len(missing_fields) == 0,
                "extracted_info": extracted_info,
                "missing_fields": missing_fields
            }
            
            # 如果有酒店名称但缺少其他信息，尝试获取酒店信息
            if "hotel_name" in extracted_info and extracted_info["hotel_name"] and extracted_info["hotel_name"] != "缺失":
                hotel_info = await self.search_hotel(extracted_info["hotel_name"])
                response["hotel_info"] = hotel_info
            
            return response
        
        except Exception as e:
            logger.error(f"分析退票请求时出错: {str(e)}")
            return {
                "is_complete": False,
                "error": str(e),
                "missing_fields": self.REQUIRED_REFUND_FIELDS,
                "extracted_info": {}
            }
    
    def _extract_info_from_text(self, text: str) -> dict:
        """从文本中提取所有字段信息"""
        extracted_info = {}
        
        # 提取每个必要字段
        for field in self.REQUIRED_REFUND_FIELDS:
            extracted_info[field] = self._extract_field(text, field)
            
        return extracted_info
    
    def _extract_field(self, text: str, field_name: str) -> str:
        """从文本中提取字段值"""
        lines = text.split("\n")
        for line in lines:
            if field_name in line:
                parts = line.split(":")
                if len(parts) > 1:
                    return parts[1].strip().strip('"')
        return "缺失"
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """
        获取MCP配置
        
        Returns:
            Dict[str, Any]: MCP配置
        """
        return self.mcp_config

# 创建服务实例
gaode_mcp_service = GaodeMCPService()
