"""通义千问图像理解服务模块

这个模块提供了使用通义千问API进行图像理解和分析的服务。
"""

import os
import base64
from typing import Dict, Any, Optional, List
import logging

# 导入OpenAI客户端
try:
    from openai import OpenAI
except ImportError:
    logging.warning("OpenAI依赖库未安装，请安装openai")

class QwenVisionService:
    """通义千问图像理解服务类，负责调用通义千问API进行图像分析"""
    
    def __init__(self):
        """初始化通义千问图像理解服务"""
        # 获取API密钥
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            logging.warning("未设置DASHSCOPE_API_KEY环境变量，通义千问API将无法使用")
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        ) if self.api_key else None
        
        # 默认使用的模型
        self.model = "qwen-vl-plus"
    
    async def analyze_image(self, image_path: str, prompt: str = "请分析这张图片并提取所有可见的文本和关键信息", is_url: bool = False) -> Dict[str, Any]:
        """使用通义千问API分析图片
        
        Args:
            image_path: 图像文件路径或URL
            prompt: 提示词，指导模型如何分析图片
            is_url: 是否为URL链接，如果为True则直接使用URL，否则读取本地文件
            
        Returns:
            包含分析结果的字典
        """
        if not self.client:
            raise ValueError("通义千问API客户端未初始化，请检查DASHSCOPE_API_KEY环境变量")
        
        try:
            # 构建图像URL
            if is_url:
                image_url = image_path
            else:
                # 读取图片并转换为base64
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                image_url = f"data:image/jpeg;base64,{image_data}"
            
            # 构建API请求
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }]
            )
            
            # 解析响应
            response = completion.choices[0].message.content
            
            # 返回分析结果
            return {"raw_response": response}
            
        except Exception as e:
            logging.error(f"通义千问API调用失败: {str(e)}")
            return {"error": f"图像分析失败: {str(e)}"}
    
    async def extract_structured_info(self, image_path: str, image_type: str = "auto", is_url: bool = False) -> Dict[str, Any]:
        """从图片中提取结构化信息
        
        Args:
            image_path: 图像文件路径或URL
            image_type: 图像类型，可以是'hotel', 'flight'或'auto'(自动检测)
            is_url: 是否为URL链接，如果为True则直接使用URL，否则读取本地文件
            
        Returns:
            包含提取信息的字典
        """
        # 根据图像类型构建不同的提示词
        if image_type == "hotel":
            prompt = """这是一张酒店预订凭证或收据。请提取以下信息：
1. 酒店名称
2. 预订确认号
3. 入住和退房日期
4. 客人姓名
5. 房间类型
6. 价格信息
7. 其他重要细节

请以JSON格式返回，包含以下结构：
{
  "hotel": {
    "name": "酒店名称",
    "confirmation_number": "确认号",
    "check_in_time": "入住日期",
    "check_out_time": "退房日期",
    "price": "价格",
    "room_type": "房间类型",
    "address": "地址"
  },
  "personal": {
    "name": "客人姓名",
    "email": "电子邮箱",
    "phone": "电话号码"
  }
}"""
        elif image_type == "flight":
            prompt = """这是一张机票或航班预订凭证。请提取以下信息：
1. 航空公司名称
2. 航班号
3. 出发和到达机场及时间
4. 乘客姓名
5. 预订确认号或票号
6. 价格信息
7. 其他重要细节

请以JSON格式返回，包含以下结构：
{
  "flight": {
    "airline": "航空公司",
    "flight_number": "航班号",
    "confirmation_number": "确认号",
    "ticket_number": "票号",
    "depart_time": "出发时间",
    "arrival_time": "到达时间",
    "price": "价格",
    "depart_airport": {
      "code": "机场代码",
      "name": "机场名称"
    },
    "arrival_airport": {
      "code": "机场代码",
      "name": "机场名称"
    }
  },
  "personal": {
    "name": "乘客姓名",
    "email": "电子邮箱",
    "phone": "电话号码"
  }
}"""
        else:  # auto或其他类型
            prompt = """请分析这张图片，识别它是什么类型的文档（如酒店预订、机票、发票等），并提取所有重要信息。

如果是酒店预订，请提取酒店名称、确认号、入住退房日期、客人信息等。
如果是机票，请提取航空公司、航班号、出发到达信息、乘客信息等。

请以JSON格式返回，包含以下结构：
{
  "detected_type": "识别的文档类型(hotel/flight/general)",
  "raw_text": "图片中的所有文本",
  "hotel": { /* 如果是酒店预订，填充酒店信息 */ },
  "flight": { /* 如果是机票，填充航班信息 */ },
  "personal": { /* 个人信息 */ }
}"""
        
        # 调用API分析图片
        result = await self.analyze_image(image_path, prompt, is_url=is_url)
        
        if "error" in result:
            return result
        
        # 尝试解析API返回的文本为结构化信息
        try:
            # 这里需要进一步处理API返回的文本，提取JSON部分
            # 由于通义千问返回的是自然语言文本，可能需要额外处理来提取JSON
            raw_response = result.get("raw_response", "")
            
            # 简单处理：尝试从文本中提取JSON部分
            import json
            import re
            
            # 尝试查找JSON格式的文本
            json_pattern = r'\{[\s\S]*\}'
            json_match = re.search(json_pattern, raw_response)
            
            if json_match:
                json_str = json_match.group(0)
                extracted_info = json.loads(json_str)
            else:
                # 如果没有找到JSON，则构建一个基本结构
                extracted_info = {
                    "detected_type": "general",
                    "raw_text": raw_response,
                    "personal": {},
                    "hotel": {},
                    "flight": {}
                }
            
            # 确保返回结果包含必要的字段
            if "detected_type" not in extracted_info:
                # 根据内容推断类型
                if "hotel" in extracted_info and extracted_info["hotel"]:
                    extracted_info["detected_type"] = "hotel"
                elif "flight" in extracted_info and extracted_info["flight"]:
                    extracted_info["detected_type"] = "flight"
                else:
                    extracted_info["detected_type"] = "general"
            
            # 添加原始文本
            if "raw_text" not in extracted_info:
                extracted_info["raw_text"] = raw_response
            
            return extracted_info
            
        except Exception as e:
            logging.error(f"解析通义千问API响应失败: {str(e)}")
            return {
                "detected_type": "general",
                "raw_text": result.get("raw_response", ""),
                "error": f"解析响应失败: {str(e)}",
                "personal": {},
                "hotel": {},
                "flight": {}
            }