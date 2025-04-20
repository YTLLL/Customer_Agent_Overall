"""酒店服务 Reasoning Agent 主入口文件

这个模块提供了FastAPI应用的主入口点，负责初始化和启动API服务。
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 导入WebSocket服务
from agent.app.services.websocket_service import connection_manager

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(
    title="酒店服务 Reasoning Agent",
    description="针对中老年人群的酒店换房/退租需求的智能代理系统",
    version="0.1.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入路由
from agent.app.api.routes import router as api_router
app.include_router(api_router)

# 添加WebSocket路由
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await connection_manager.connect(websocket, user_id)
    try:
        while True:
            # 保持连接活跃
            data = await websocket.receive_text()
            # 可以处理前端发来的命令，如请求历史消息等
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, user_id)

# 主函数
def main():
    """启动FastAPI应用服务器"""
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    # 启动服务器
    uvicorn.run(
        "agent.app.main:app",
        host=host,
        port=port,
        reload=True  # 开发模式下启用热重载
    )

if __name__ == "__main__":
    main()