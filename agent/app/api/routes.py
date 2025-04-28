"""API路由模块

这个模块定义了所有API端点的路由处理。
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pymongo import MongoClient
from agent.app.models.conversation import Conversation, ConversationStatus, Message
from agent.app.services.agent_service import AgentService
from agent.app.services.calling_agent_service import CallingAgentService
from agent.app.services.calling_db_service import CallingDBService
from agent.app.services.db_service import DBService
from typing import Union

# 创建路由器
router = APIRouter(prefix="/api", tags=["api"])
client = MongoClient("mongodb://localhost:27017")
db = client["hotel_db"]
collection = db["refund_prompts"]
# 依赖注入
def get_agent_service():
    """获取Agent服务实例"""
    return AgentService()
def get_calling_agent_service():
    return CallingAgentService()
def get_db_service():
    """获取数据库服务实例"""
    return DBService()
def get_calling_db_service():
    return CallingDBService()
from agent.app.agents.summary_agent import SummaryAgent
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

@router.post("/callingconversation", response_model=ConversationResponse)
async def create_or_continue_conversation(
    request: ConversationRequest,
    agent_service: CallingAgentService = Depends(get_calling_agent_service),
    db_service: CallingDBService = Depends(get_calling_db_service)
):
    print("create ")
    """创建新对话或继续现有对话，并同步返回代理生成内容"""
    # 查找用户现有的活跃对话
    conversation = db_service.get_active_conversation(request.user_id)
    print("here")
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

    # ✅ 直接调用 agent_service，同步生成回复
    reply_message = await agent_service.process_message(
        conversation.id,
        request.message,
        request.user_id
    )

    # ✅ 把 agent 回复也存进去
    assistant_message = Message(
        role="assistant",
        content=reply_message
    )
    conversation.add_message(assistant_message)
    db_service.save_message(conversation.id, assistant_message)

    # ✅ 返回最新消息列表
    return ConversationResponse(
        conversation_id=conversation.id,
        messages=[msg.dict() for msg in conversation.messages],
        status=conversation.status.value
    )


@router.get("/callingconversation/{conversation_id}", response_model=ConversationResponse)
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
    print("add newe as new meta data ")
    conversation.metadata['newe'] = 'something'
    # summary_agent = SummaryAgent()
    # summary = await summary_agent.generate_summary(conversation)
    #
    # # ✅ 打印 summary 内容用于调试
    # print("🔥 生成的对话总结：", summary)
    return ConversationResponse(
        conversation_id=conversation.id,
        messages=[msg.dict() for msg in conversation.messages],
        status=conversation.status.value
    )
@router.post("/callingconversation/{conversation_id}/end")
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

    # ✅ 正确地 await 调用 SummaryAgent 的异步方法
    summary_agent = SummaryAgent()
    summary = await summary_agent.generate_summary(conversation)

    # ✅ 打印 summary 内容用于调试
    print("🔥 生成的对话总结：", summary)

    # ✅ 保存到 metadata 中
    conversation.metadata["summary"] = summary
    db_service.update_conversation(conversation)

    return {
        "status": "success",
        "message": "对话已结束",
        "summary": summary
    }

class FlightInfo(BaseModel):
    timestamp: int
    name: str
    details: Optional[str] = None


class HotelInfo(BaseModel):
    timestamp: str
    name: str
    details: Optional[str] = None


# 定义请求体
class UserRequest(BaseModel):
    flightInfo: Union[FlightInfo, HotelInfo]
    userId: str
    phoneNumber: str
    otherPersonalInfo: str
    name: str


# 定义返回体
class ResponseMessage(BaseModel):
    message: str


@router.post("/generate_prompt", response_model=ResponseMessage)
async def generate_prompt(request: UserRequest):
    """
    接收用户传来的信息，生成prompt并存入MongoDB
    """
    travel_info = request.flightInfo
    timestamp = travel_info.timestamp
    travel_agency_name = travel_info.name
    if isinstance(flightInfo, FlightInfo):
        type = "航班"
    else:
        type = "酒店"

    try:
        # 生成 prompt
        prompt = (
            f"你是客户代表，请根据以下信息帮用户和第三方平台联系：\n\n"
            f"{type}名称：{travel_agency_name}\n"
            f"时间：{timestamp}\n"
            f"📞 联系电话: {request.phone_number}\n"
            f"👤 客户姓名: {request.name}\n"
            f"📝 客户诉求: {request.otherPersonalInfo}\n\n"
            f"请用专业、礼貌的口吻，帮助用户表达诉求。"
        )
        print("保存数据")
        # 存入MongoDB
        record = {
            "user_id": request.userId,
            "phone_number": request.phoneNumber,
            "customer_name": request.name,
            "personal_info": request.otherPersonalInfo,
            "travel_agency_name": travel_agency_name,
            "timestamp": timestamp,
            "prompt": prompt
        }
        collection.insert_one(record)

        return ResponseMessage(message="✅ Prompt已生成并保存到数据库。")

    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/callingconversation", response_model=ConversationResponse)
# async def create_or_continue_conversation(
#     request: ConversationRequest,
#     background_tasks: BackgroundTasks,
#     agent_service: CallingAgentService = Depends(get_calling_agent_service),
#     db_service: CallingDBService = Depends(get_calling_db_service)
# ):
#     """创建新对话或继续现有对话"""
#     # 查找用户现有的活跃对话
#     conversation = db_service.get_active_conversation(request.user_id)
#
#     # 如果没有活跃对话，创建新对话
#     if not conversation:
#         conversation = Conversation(
#             user_id=request.user_id,
#             channel=request.channel,
#             metadata=request.metadata or {}
#         )
#         db_service.save_conversation(conversation)
#
#     # 添加用户消息
#     user_message = Message(
#         role="user",
#         content=request.message
#     )
#     conversation.add_message(user_message)
#     db_service.save_message(conversation.id, user_message)
#
#     # 在后台处理代理响应
#     background_tasks.add_task(
#         agent_service.process_message,
#         conversation.id,
#         request.message
#     )
#
#     # 返回当前对话状态
#     return ConversationResponse(
#         conversation_id=conversation.id,
#         messages=[msg.dict() for msg in conversation.messages],
#         status=conversation.status.value
#     )
#
# @router.get("/callingconversation/{conversation_id}", response_model=ConversationResponse)
# async def get_conversation(
#     conversation_id: str,
#     db_service: DBService = Depends(get_db_service)
# ):
#     """获取特定对话的详情"""
#     conversation = db_service.get_conversation(conversation_id)
#     if not conversation:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"对话 {conversation_id} 不存在"
#         )
#     print("add newe as new meta data ")
#     conversation.metadata['newe'] = 'something'
#     # summary_agent = SummaryAgent()
#     # summary = await summary_agent.generate_summary(conversation)
#     #
#     # # ✅ 打印 summary 内容用于调试
#     # print("🔥 生成的对话总结：", summary)
#     return ConversationResponse(
#         conversation_id=conversation.id,
#         messages=[msg.dict() for msg in conversation.messages],
#         status=conversation.status.value
#     )
# @router.post("/callingconversation/{conversation_id}/end")
# async def end_conversation(
#     conversation_id: str,
#     db_service: DBService = Depends(get_db_service),
#     agent_service: AgentService = Depends(get_agent_service)
# ):
#     """结束对话并生成总结"""
#     conversation = db_service.get_conversation(conversation_id)
#     if not conversation:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"对话 {conversation_id} 不存在"
#         )
#
#     # 更新对话状态为已完成
#     conversation.status = ConversationStatus.COMPLETED
#
#     # ✅ 正确地 await 调用 SummaryAgent 的异步方法
#     summary_agent = SummaryAgent()
#     summary = await summary_agent.generate_summary(conversation)
#
#     # ✅ 打印 summary 内容用于调试
#     print("🔥 生成的对话总结：", summary)
#
#     # ✅ 保存到 metadata 中
#     conversation.metadata["summary"] = summary
#     db_service.update_conversation(conversation)
#
#     return {
#         "status": "success",
#         "message": "对话已结束",
#         "summary": summary
#     }