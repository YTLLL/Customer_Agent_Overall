"""API路由模块

这个模块定义了所有API端点的路由处理。
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from agent.app.models.conversation import Conversation, ConversationStatus, Message
from agent.app.services.agent_service import AgentService
from agent.app.services.db_service import DBService

# 创建路由器
router = APIRouter(prefix="/api", tags=["api"])

# 依赖注入
def get_agent_service():
    """获取Agent服务实例"""
    return AgentService()

def get_db_service():
    """获取数据库服务实例"""
    return DBService()

# 请求模型
class ConversationRequest(BaseModel):
    """对话请求模型"""
    user_id: str
    message: str
    channel: str = "web"  # 默认为网页渠道
    metadata: Optional[Dict[str, Any]] = None

# 响应模型
class ConversationResponse(BaseModel):
    """对话响应模型"""
    conversation_id: str
    messages: List[Dict[str, Any]]
    status: str

@router.post("/conversation", response_model=ConversationResponse)
async def create_or_continue_conversation(
    request: ConversationRequest,
    background_tasks: BackgroundTasks,
    agent_service: AgentService = Depends(get_agent_service),
    db_service: DBService = Depends(get_db_service)
):
    """创建新对话或继续现有对话"""
    # 查找用户现有的活跃对话
    conversation = db_service.get_active_conversation(request.user_id)
    
    # 如果没有活跃对话，创建新对话
    if not conversation:
        conversation = Conversation(
            user_id=request.user_id,
            channel=request.channel,
            metadata=request.metadata or {}
        )
        db_service.save_conversation(conversation)
    
    # 添加用户消息
    user_message = Message(
        role="user",
        content=request.message
    )
    conversation.add_message(user_message)
    db_service.save_message(conversation.id, user_message)
    
    # 在后台处理代理响应
    background_tasks.add_task(
        agent_service.process_message,
        conversation.id,
        request.message
    )
    
    # 返回当前对话状态
    return ConversationResponse(
        conversation_id=conversation.id,
        messages=[msg.dict() for msg in conversation.messages],
        status=conversation.status.value
    )

@router.get("/conversation/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db_service: DBService = Depends(get_db_service)
):
    """获取特定对话的详情"""
    conversation = db_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"对话 {conversation_id} 不存在"
        )
    
    return ConversationResponse(
        conversation_id=conversation.id,
        messages=[msg.dict() for msg in conversation.messages],
        status=conversation.status.value
    )

@router.post("/conversation/{conversation_id}/end")
async def end_conversation(
    conversation_id: str,
    db_service: DBService = Depends(get_db_service),
    agent_service: AgentService = Depends(get_agent_service)
):
    """结束对话并生成总结"""
    conversation = db_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"对话 {conversation_id} 不存在"
        )
    
    # 更新对话状态为已完成
    conversation.status = ConversationStatus.COMPLETED
    db_service.update_conversation(conversation)
    
    # 生成对话总结
    summary = agent_service.generate_summary(conversation)
    
    return {"status": "success", "message": "对话已结束", "summary": summary}