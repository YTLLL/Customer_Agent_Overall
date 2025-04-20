"""对话模型模块

这个模块定义了对话和消息的数据模型。
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ConversationStatus(str, Enum):
    """对话状态枚举"""
    ACTIVE = "active"  # 活跃状态
    PENDING = "pending"  # 等待用户回复
    COMPLETED = "completed"  # 已完成
    TIMEOUT = "timeout"  # 超时

class Message(BaseModel):
    """消息模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # user 或 assistant
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

class Conversation(BaseModel):
    """对话模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    channel: str  # 沟通渠道: web, phone, message, whatsapp, email
    status: ConversationStatus = ConversationStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: List[Message] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    goal_achieved: bool = False
    summary: Optional[str] = None
    
    def add_message(self, message: Message):
        """添加消息到对话"""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def is_timeout(self, timeout_hours: int = 6) -> bool:
        """检查对话是否超时"""
        time_diff = datetime.now() - self.updated_at
        return time_diff.total_seconds() / 3600 > timeout_hours
    
    def dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "channel": self.channel,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [msg.dict() for msg in self.messages],
            "metadata": self.metadata,
            "goal_achieved": self.goal_achieved,
            "summary": self.summary
        }