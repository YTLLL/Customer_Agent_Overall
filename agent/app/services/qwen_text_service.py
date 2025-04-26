"""通义千问文本理解服务模块

该模块提供了使用通义千问API进行文本理解和分析的服务。
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    logging.warning("OpenAI依赖库未安装，请安装openai")

class QwenTextService:
    """通义千问文本理解服务类，负责调用通义千问API进行文本分析"""
    def __init__(self):
        # 尝试从.env文件直接加载环境变量
        load_dotenv()
        
        # 尝试获取API密钥
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        
        # 如果环境变量中没有API密钥，尝试从.env文件中读取
        if not self.api_key:
            try:
                # 尝试直接读取.env文件
                env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), '.env')
                if os.path.exists(env_path):
                    with open(env_path, 'r') as f:
                        for line in f:
                            if line.startswith('DASHSCOPE_API_KEY='):
                                self.api_key = line.strip().split('=', 1)[1].strip('"\'')
                                break
            except Exception as e:
                logging.error(f"读取.env文件失败: {str(e)}")
        
        if not self.api_key:
            logging.warning("未设置DASHSCOPE_API_KEY环境变量，通义千问API将无法使用")
        
        self.client = None
        self.model = "qwen-turbo"
        self.update_client()
        
    def update_client(self):
        """更新API客户端实例。如果环境变量已更新，调用此方法可重新初始化客户端"""
        # 重新获取API密钥
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            return True
        return False

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