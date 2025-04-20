"""数据库服务模块

这个模块提供了与MongoDB数据库交互的服务。
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from agent.app.models.conversation import Conversation, Message, ConversationStatus

class DBService:
    """数据库服务类，负责对话数据的存储和检索"""
    
    def __init__(self):
        """初始化MongoDB数据库服务"""
        # 获取MongoDB连接URI
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB_NAME", "hotel_db")
        
        # 连接到MongoDB
        self.client = MongoClient(mongo_uri)
        self.db: Database = self.client[db_name]
        
        # 获取集合
        self.conversations: Collection = self.db.conversations
        self.messages: Collection = self.db.messages
    
    def save_conversation(self, conversation: Conversation) -> None:
        """保存对话到MongoDB数据库"""
        # 将Pydantic模型转换为字典并保存到MongoDB
        # 手动创建不包含messages的字典
        conv_dict = conversation.dict()
        if "messages" in conv_dict:
            del conv_dict["messages"]
            
        self.conversations.update_one(
            {"id": conversation.id},
            {"$set": conv_dict},
            upsert=True
        )
    
    def update_conversation(self, conversation: Conversation) -> None:
        """更新对话信息"""
        # 更新时间戳
        conversation.updated_at = datetime.now()
        self.save_conversation(conversation)
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """根据ID从MongoDB获取对话"""
        data = self.conversations.find_one({"id": conversation_id})
        if not data:
            return None
        
        # 重建对话对象
        conversation = Conversation(
            id=data["id"],
            user_id=data["user_id"],
            channel=data["channel"],
            status=ConversationStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"],
            metadata=data["metadata"],
            goal_achieved=data.get("goal_achieved", False),
            summary=data.get("summary")
        )
        
        # 加载消息
        conversation.messages = self.get_messages(conversation_id)
        
        return conversation
    
    def get_active_conversation(self, user_id: str) -> Optional[Conversation]:
        """获取用户的活跃对话"""
        # 查询MongoDB中该用户的活跃对话
        data = self.conversations.find_one({
            "user_id": user_id,
            "status": {"$in": [ConversationStatus.ACTIVE.value, ConversationStatus.PENDING.value]}
        })
        
        if data:
            return self.get_conversation(data["id"])
        
        return None
    
    def save_message(self, conversation_id: str, message: Message) -> None:
        """保存消息到MongoDB数据库"""
        # 将消息保存到MongoDB，添加conversation_id字段以便查询
        message_data = message.dict()
        message_data["conversation_id"] = conversation_id
        
        # 保存消息
        self.messages.update_one(
            {"id": message.id},
            {"$set": message_data},
            upsert=True
        )
    
    def get_messages(self, conversation_id: str) -> List[Message]:
        """从MongoDB获取对话的所有消息"""
        messages = []
        
        # 查询指定对话的所有消息，并按时间戳排序
        cursor = self.messages.find({"conversation_id": conversation_id}).sort("timestamp", 1)
        
        # 遍历所有消息记录
        for data in cursor:
            # 创建消息对象
            message = Message(
                id=data["id"],
                role=data["role"],
                content=data["content"],
                timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
                metadata=data["metadata"]
            )
            messages.append(message)
        
        return messages
    
    def check_timeout_conversations(self, timeout_hours: int = 6) -> List[Conversation]:
        """检查并更新超时的对话"""
        timeout_conversations = []
        
        # 查询所有活跃状态的对话
        active_conversations = self.conversations.find({
            "status": {"$in": [ConversationStatus.ACTIVE.value, ConversationStatus.PENDING.value]}
        })
        
        # 遍历所有活跃对话
        for data in active_conversations:
            # 获取完整对话
            conversation = self.get_conversation(data["id"])
            
            # 检查是否超时
            if conversation and conversation.is_timeout(timeout_hours):
                conversation.status = ConversationStatus.TIMEOUT
                self.update_conversation(conversation)
                timeout_conversations.append(conversation)
        
        return timeout_conversations