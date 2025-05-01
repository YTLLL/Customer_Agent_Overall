"""WebSocket服务模块

该模块提供了WebSocket连接管理和消息广播功能。
"""

import logging
from typing import Dict, List, Any
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket连接管理器
    
    负责管理WebSocket连接和消息广播。
    """
    
    def __init__(self):
        """初始化连接管理器"""
        # 用户ID到WebSocket连接的映射
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """建立WebSocket连接
        
        Args:
            websocket: WebSocket连接
            user_id: 用户ID
        """
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"用户 {user_id} 建立了WebSocket连接")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """断开WebSocket连接
        
        Args:
            websocket: WebSocket连接
            user_id: 用户ID
        """
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"用户 {user_id} 断开了WebSocket连接")
    
    async def send_message(self, user_id: str, message: str):
        """向指定用户发送文本消息
        
        Args:
            user_id: 用户ID
            message: 消息内容
        """
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(message)
            logger.debug(f"向用户 {user_id} 发送了消息: {message[:50]}...")
    
    async def broadcast_to_user(self, user_id: str, message_type: str, data: Any):
        """向指定用户广播JSON消息
        
        Args:
            user_id: 用户ID
            message_type: 消息类型
            data: 消息数据
        """
        message = {
            "type": message_type,
            "data": data
        }
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)
            logger.debug(f"向用户 {user_id} 广播了 {message_type} 类型的消息")
    
    async def broadcast_feedback(self, user_id: str, feedback_type: str, content: str, metadata: Dict[str, Any] = None):
        """向用户广播反馈消息
        
        Args:
            user_id: 用户ID
            feedback_type: 反馈类型，如'error', 'info', 'success', 'warning'
            content: 反馈内容
            metadata: 额外的元数据
        """
        data = {
            "feedback_type": feedback_type,
            "content": content
        }
        if metadata:
            data["metadata"] = metadata
        
        await self.broadcast_to_user(user_id, "feedback", data)

# 创建全局连接管理器实例
connection_manager = ConnectionManager()
