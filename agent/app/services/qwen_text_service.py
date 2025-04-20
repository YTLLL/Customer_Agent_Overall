"""通义千问文本理解服务模块

该模块提供了使用通义千问API进行文本理解和分析的服务。
"""

import os
import logging
from typing import Dict, Any

try:
    from openai import OpenAI
except ImportError:
    logging.warning("OpenAI依赖库未安装，请安装openai")

class QwenTextService:
    """通义千问文本理解服务类，负责调用通义千问API进行文本分析"""
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            logging.warning("未设置DASHSCOPE_API_KEY环境变量，通义千问API将无法使用")
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        ) if self.api_key else None
        self.model = "qwen-turbo"

    async def analyze_text(self, text: str, prompt: str = "请分析以下文本并提取关键信息") -> Dict[str, Any]:
        """使用通义千问API分析文本
        Args:
            text: 需要分析的文本
            prompt: 指导模型如何分析文本
        Returns:
            包含分析结果的字典
        """
        if not self.client:
            raise ValueError("通义千问API客户端未初始化，请检查DASHSCOPE_API_KEY环境变量")
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt + "\n" + text}
                    ]
                }]
            )
            response = completion.choices[0].message.content
            return {"raw_response": response}
        except Exception as e:
            logging.error(f"通义千问API调用失败: {str(e)}")
            return {"error": f"文本分析失败: {str(e)}"}