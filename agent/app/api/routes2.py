from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from pymongo import MongoClient
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from agent.app.models.conversation import Conversation, ConversationStatus, Message
from agent.app.services.agent_service import AgentService
from agent.app.services.calling_agent_service import CallingAgentService
from agent.app.services.calling_db_service import CallingDBService
from agent.app.services.db_service import DBService

# 创建路由器
router = APIRouter(prefix="/api", tags=["api"])
# 初始化 MongoDB 连接（你改成自己的URI和DB名）


# 定义请求体
class UserRequest(BaseModel):
    hotel_name: str
    user_id: str
    phone_number: str
    personal_info: str
    name: str

# 定义返回体
class ResponseMessage(BaseModel):
    message: str

@router.post("/generate_prompt", response_model=ResponseMessage)
async def generate_prompt(request: UserRequest):
    """
    接收用户传来的信息，生成prompt并存入MongoDB
    """
    try:
        # 生成 prompt
        prompt = (
            f"你是客户代表，请根据以下信息帮用户和第三方平台联系：\n\n"
            f"🏨 酒店名称: {request.hotel_name}\n"
            f"📞 联系电话: {request.phone_number}\n"
            f"👤 客户姓名: {request.name}\n"
            f"📝 客户诉求: {request.personal_info}\n\n"
            f"请用专业、礼貌的口吻，帮助用户表达诉求。"
        )

        # 存入MongoDB
        record = {
            "user_id": request.user_id,
            "hotel_name": request.hotel_name,
            "phone_number": request.phone_number,
            "customer_name": request.name,
            "personal_info": request.personal_info,
            "prompt": prompt,
            "created_at": datetime.utcnow()  # 存时间戳
        }
        collection.insert_one(record)

        return ResponseMessage(message="✅ Prompt已生成并保存到数据库。")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
