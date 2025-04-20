"""工具函数模块

这个模块提供了各种辅助函数，用于支持代理系统的运行。
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def setup_environment():
    """设置环境，确保必要的目录和文件存在"""
    # 获取数据库路径
    db_path = Path(os.getenv("DB_PATH", "./data/hotel_db"))
    
    # 创建数据库目录
    conversations_path = db_path / "conversations"
    messages_path = db_path / "messages"
    
    conversations_path.mkdir(parents=True, exist_ok=True)
    messages_path.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"环境设置完成，数据库路径: {db_path}")

def format_hotel_info(hotel_data: Dict[str, Any]) -> str:
    """格式化酒店信息，用于代理回复"""
    if not hotel_data:
        return "未找到酒店信息"
    
    info = f"酒店名称: {hotel_data.get('name', '未知')}\n"
    info += f"地址: {hotel_data.get('address', '未知')}\n"
    info += f"电话: {hotel_data.get('phone', '未知')}\n"
    info += f"退房政策: {hotel_data.get('checkout_policy', '未知')}\n"
    
    return info

def extract_hotel_name(message: str) -> str:
    """从用户消息中提取酒店名称
    
    这个函数在实际应用中可以使用更复杂的NLP技术来提取实体
    """
    # 简单实现，实际项目中应使用NER或其他技术
    keywords = ["酒店", "宾馆", "旅馆"]
    
    for keyword in keywords:
        if keyword in message:
            start_index = message.find(keyword) - 10
            end_index = message.find(keyword) + 10
            
            if start_index < 0:
                start_index = 0
            if end_index > len(message):
                end_index = len(message)
            
            return message[start_index:end_index]
    
    return ""

def check_conversation_health(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """检查对话健康状态，用于监控和改进系统"""
    if not messages:
        return {"status": "empty", "turns": 0}
    
    # 计算对话轮次
    turns = len([msg for msg in messages if msg["role"] == "user"])
    
    # 检查是否有长时间无回复
    response_times = []
    for i in range(1, len(messages)):
        if messages[i]["role"] == "assistant" and messages[i-1]["role"] == "user":
            user_time = messages[i-1]["timestamp"]
            assistant_time = messages[i]["timestamp"]
            response_time = (assistant_time - user_time).total_seconds()
            response_times.append(response_time)
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    return {
        "status": "active",
        "turns": turns,
        "avg_response_time": avg_response_time,
        "health": "good" if avg_response_time < 5 else "slow"
    }