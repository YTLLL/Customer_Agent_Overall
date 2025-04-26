#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
终端对话脚本

这个脚本允许用户通过终端与酒店服务代理进行对话，测试各种功能。
"""

import os
import sys
import json
import uuid
import asyncio
from datetime import datetime
import requests
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入项目模块
from agent.app.models.conversation import Conversation, Message
from agent.app.agents.reasoning_graph import ReasoningGraph

# 加载环境变量
load_dotenv()

# 检查必要的环境变量
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("警告: DASHSCOPE_API_KEY环境变量未设置，请手动输入API密钥")
    api_key = input("请输入您的DASHSCOPE_API_KEY (或按Enter跳过): ")
    if api_key:
        # 在初始化推理图之前设置环境变量
        os.environ["DASHSCOPE_API_KEY"] = api_key
        print("已设置DASHSCOPE_API_KEY环境变量")
    else:
        print("未提供API密钥，部分功能可能无法正常工作")

# 重新加载环境变量，确保所有模块都能访问到最新的环境变量
if 'DASHSCOPE_API_KEY' in os.environ:
    print(f"使用API密钥: {os.environ['DASHSCOPE_API_KEY'][:10]}...")

# 初始化推理图
reasoning_graph = ReasoningGraph()

# 如果环境变量已设置，更新API客户端
if 'DASHSCOPE_API_KEY' in os.environ:
    # 更新推理图中的QwenTextService客户端
    if reasoning_graph.qwen_service.update_client():
        print("成功更新API客户端")

async def create_conversation():
    """创建一个新的对话"""
    user_id = f"terminal_user_{uuid.uuid4().hex[:8]}"
    conversation_id = str(uuid.uuid4())
    
    # 创建基本的对话元数据，初始为空，将在对话过程中从高德MCP服务获取真实酒店信息
    metadata = {}
    
    # 创建对话对象
    conversation = Conversation(
        id=conversation_id,
        user_id=user_id,
        channel="terminal",  # 添加channel字段
        messages=[],
        metadata=metadata,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    return conversation

async def chat_loop(conversation):
    """对话循环"""
    print("=== 酒店服务与退票Agent终端对话 ===\n")
    print(f"用户ID: {conversation.user_id}")
    print(f"对话ID: {conversation.id}\n")
    
    # 导入必要的服务
    from agent.app.services.agent_service import AgentService
    from agent.app.services.gaode_mcp_service import gaode_mcp_service
    from agent.app.services.db_service import DBService
    
    # 初始化服务
    agent_service = AgentService()
    db_service = DBService()
    
    while True:
        # 获取用户输入
        user_input = input("\n请输入消息 (输入'exit'退出，输入'metadata'查看元数据): ")
        
        # 检查特殊命令
        if user_input.lower() == 'exit':
            print("\n退出程序")
            break
        elif user_input.lower() == 'metadata':
            # 更新元数据，显示从上下文记忆中获取的酒店信息
            context = agent_service.conversation_contexts.get(conversation.id, {})
            
            # 清空元数据，确保不会显示示例内容
            conversation.metadata = {}
            
            # 如果上下文中有酒店名称但没有酒店信息，尝试获取酒店信息
            if context.get("hotel_name") and not context.get("hotel_info"):
                hotel_name = context["hotel_name"]
                print(f"尝试获取酒店信息: {hotel_name}")
                hotel_info = await gaode_mcp_service.search_hotel(hotel_name)
                if hotel_info:
                    context["hotel_info"] = hotel_info
                    agent_service.conversation_contexts[conversation.id] = context
                    print(f"成功获取酒店信息: {hotel_info}")
            
            # 将酒店信息添加到元数据中
            if context.get("hotel_info"):
                conversation.metadata["hotel_info"] = context["hotel_info"]
                
                # 更新数据库中的对话元数据
                db_service.update_conversation(conversation)
            
            print("\n=== 对话元数据 ===")
            print(json.dumps(conversation.metadata, ensure_ascii=False, indent=2))
            continue
        
        # 添加用户消息到对话
        user_message = Message(role="user", content=user_input)
        conversation.add_message(user_message)
        
        print("\n处理中...")
        try:
            # 处理用户消息并更新上下文记忆
            print("开始处理用户请求...")
            # 先获取当前对话中的消息数量
            messages_before = len(conversation.messages)
            
            # 调用agent_service处理消息
            await agent_service.process_message(conversation.id, user_input)
            
            # 重新获取对话，确保我们有最新的消息
            try:
                # db_service.get_conversation 是同步方法，不需要 await
                updated_conversation = db_service.get_conversation(conversation.id)
                if updated_conversation:
                    conversation = updated_conversation
            except Exception as e:
                print(f"获取更新后的对话时出错: {str(e)}")
            
            # 检查是否有新的助手消息被添加
            if len(conversation.messages) > messages_before:
                # 如果有新消息，获取最新的助手消息
                for i in range(len(conversation.messages)-1, -1, -1):
                    if conversation.messages[i].role == "assistant":
                        response = conversation.messages[i].content
                        print("使用通义千问API生成回复...")
                        break
            else:
                # 如果没有新消息，使用推理图处理用户消息
                print("agent_service没有生成新的助手消息，使用推理图生成回复...")
                response = await reasoning_graph.process_request(conversation, user_input)
                
                # 添加助手消息到对话
                assistant_message = Message(role="assistant", content=response)
                conversation.add_message(assistant_message)
                # 保存消息到数据库
                # db_service.save_message 是同步方法，不需要 await
                db_service.save_message(conversation.id, assistant_message)
            
            # 更新元数据，显示从上下文记忆中获取的酒店信息
            context = agent_service.conversation_contexts.get(conversation.id, {})
            
            # 如果上下文中有酒店名称但没有酒店信息，尝试获取酒店信息
            if context.get("hotel_name") and not context.get("hotel_info"):
                hotel_name = context["hotel_name"]
                print(f"尝试获取酒店信息: {hotel_name}")
                hotel_info = await gaode_mcp_service.search_hotel(hotel_name)
                if hotel_info:
                    context["hotel_info"] = hotel_info
                    agent_service.conversation_contexts[conversation.id] = context
                    print(f"成功获取酒店信息: {hotel_info}")
            
            # 清空元数据，确保不会显示示例内容
            conversation.metadata = {}
            
            # 将酒店信息添加到元数据中
            if context.get("hotel_info"):
                conversation.metadata["hotel_info"] = context["hotel_info"]
                
                # 更新数据库中的对话元数据
                db_service.update_conversation(conversation)
            
            # 显示助手回复
            print(f"\n机器人: {response}")
            
        except Exception as e:
            print(f"\n错误: {str(e)}")

async def main():
    """主函数"""
    # 创建对话
    conversation = await create_conversation()
    
    # 开始对话循环
    await chat_loop(conversation)

if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
