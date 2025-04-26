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
            
            # 处理用户输入，无论是文字还是图片，都尝试提取酒店信息
            # 如果上下文为空，尝试从用户输入中提取酒店信息
            if not context:
                # 检查是否是文字输入
                if "酒店" in user_input or "宾馆" in user_input or "旅馆" in user_input:
                    from agent.app.utils.helpers import extract_hotel_name
                    hotel_name = extract_hotel_name(user_input)
                    if hotel_name:
                        context["hotel_name"] = hotel_name
                        print(f"从用户文字消息中提取到酒店名称: {hotel_name}")
                        # 保存上下文到agent_service
                        agent_service.conversation_contexts[conversation.id] = context
                # 注意: 这里可以添加图片处理逻辑，如果用户上传了酒店图片
                # elif 检测到图片:
                #     hotel_name = 从图片中提取酒店名称()
                #     if hotel_name:
                #         context["hotel_name"] = hotel_name
                #         print(f"从用户图片中提取到酒店名称: {hotel_name}")
                #         agent_service.conversation_contexts[conversation.id] = context
            
            # 如果上下文中有酒店名称但没有酒店信息，并且不在等待酒店选择状态，尝试获取酒店信息
            # 无论是通过图片还是文字输入，都尝试获取酒店信息
            if context.get("hotel_name") and not context.get("hotel_info") and not context.get("waiting_for_hotel_selection", False):
                hotel_name = context["hotel_name"]
                print(f"尝试获取酒店信息: {hotel_name}")
                hotel_info = await gaode_mcp_service.search_hotel(hotel_name)
                
                # 检查是否返回了多个酒店选项
                if hotel_info and hotel_info.get("multiple_options", False):
                    # 将多个酒店选项保存到上下文中
                    context["hotel_options"] = hotel_info.get("hotels", [])  # 当前显示的酒店选项
                    context["all_hotels"] = hotel_info.get("all_hotels", [])  # 所有酒店选项
                    context["total_hotels"] = hotel_info.get("total_hotels", len(context["hotel_options"]))  # 总数量
                    context["has_more"] = hotel_info.get("has_more", False)  # 是否还有更多
                    context["current_page"] = 1  # 当前页码
                    context["waiting_for_hotel_selection"] = True
                    agent_service.conversation_contexts[conversation.id] = context
                    print(f"已将多个酒店选项保存到上下文: {context}")
                    
                    # 生成酒店选项列表供用户选择
                    hotels_list = context["hotel_options"]
                    total_hotels = context["total_hotels"]
                    
                    # 生成选项消息
                    options_message = f"找到{total_hotels}家与'{hotel_name}'匹配的酒店，以下是第1页，请选择具体是哪一家（输入对应的数字）：\n"
                    
                    # 添加酒店选项
                    for i, hotel in enumerate(hotels_list, 1):
                        # 如果有电话信息，也显示出来
                        tel_info = f" 电话: {hotel.get('tel')}" if hotel.get('tel') else ""
                        options_message += f"{i}. {hotel.get('name')} - {hotel.get('formatted_address')}{tel_info}\n"
                    
                    # 如果还有更多酒店，添加提示
                    if context["has_more"]:
                        options_message += "\n如果没有找到您需要的酒店，请输入'显示更多'或'下一页'查看更多选项。"
                    
                    # 添加选项消息到对话
                    assistant_message = Message(role="assistant", content=options_message)
                    conversation.add_message(assistant_message)
                    db_service.save_message(conversation.id, assistant_message)
                    
                    # 更新响应内容
                    response = options_message
                    print(f"需要用户选择具体酒店，已生成选项列表")
                elif hotel_info:
                    # 单个酒店信息，直接保存
                    context["hotel_info"] = hotel_info
                    agent_service.conversation_contexts[conversation.id] = context
                    print(f"成功获取唯一酒店信息并保存到上下文: {hotel_info}")
            
            # 处理用户对酒店选择的响应
            elif context.get("waiting_for_hotel_selection", False) and context.get("hotel_options"):
                try:
                    print(f"当前上下文: {context}")
                    
                    # 检查用户是否要求显示更多酒店
                    is_asking_more = any(keyword in user_input for keyword in ["显示更多", "下一页", "更多", "没有找到", "没有看到", "继续显示"])
                    
                    if is_asking_more and context.get("has_more", False) and context.get("all_hotels"):
                        # 用户要求显示更多酒店
                        current_page = context.get("current_page", 1)
                        next_page = current_page + 1
                        context["current_page"] = next_page
                        
                        # 计算下一页的酒店选项
                        all_hotels = context["all_hotels"]
                        total_hotels = context["total_hotels"]
                        items_per_page = 20  # 每页显示的酒店数量
                        
                        start_idx = (next_page - 1) * items_per_page
                        end_idx = min(start_idx + items_per_page, total_hotels)
                        
                        # 获取下一页的酒店
                        next_page_hotels = all_hotels[start_idx:end_idx]
                        context["hotel_options"] = next_page_hotels
                        
                        # 检查是否还有更多页
                        context["has_more"] = end_idx < total_hotels
                        
                        # 保存更新后的上下文
                        agent_service.conversation_contexts[conversation.id] = context
                        
                        # 生成酒店选项列表
                        options_message = f"以下是第{next_page}页的酒店选项（{start_idx+1}-{end_idx}/{total_hotels}），请选择具体是哪一家（输入对应的数字）：\n"
                        
                        # 添加酒店选项
                        for i, hotel in enumerate(next_page_hotels, 1):
                            # 如果有电话信息，也显示出来
                            tel_info = f" 电话: {hotel.get('tel')}" if hotel.get('tel') else ""
                            options_message += f"{i}. {hotel.get('name')} - {hotel.get('formatted_address')}{tel_info}\n"
                        
                        # 如果还有更多酒店，添加提示
                        if context["has_more"]:
                            options_message += "\n如果没有找到您需要的酒店，请输入'显示更多'或'下一页'查看更多选项。"
                        
                        # 添加选项消息到对话
                        assistant_message = Message(role="assistant", content=options_message)
                        conversation.add_message(assistant_message)
                        db_service.save_message(conversation.id, assistant_message)
                        response = options_message
                        return
                    
                    # 检查用户是否在询问酒店电话或其他信息
                    is_asking_phone = any(keyword in user_input for keyword in ["电话", "联系方式", "联系电话", "联系"])
                    is_asking_address = any(keyword in user_input for keyword in ["地址", "位置", "在哪里", "在哪"])
                    
                    if is_asking_phone or is_asking_address:
                        # 用户询问电话或地址，但还未选择具体酒店
                        current_page = context.get("current_page", 1)
                        options_message = f"您还没有选择具体的酒店，请先选择一家酒店（输入对应的数字），以下是第{current_page}页的酒店选项：\n"
                        for i, hotel in enumerate(context["hotel_options"], 1):
                            # 如果有电话信息，也显示出来
                            tel_info = f" 电话: {hotel.get('tel')}" if hotel.get('tel') else ""
                            options_message += f"{i}. {hotel.get('name')} - {hotel.get('formatted_address')}{tel_info}\n"
                        
                        # 如果还有更多酒店，添加提示
                        if context.get("has_more", False):
                            options_message += "\n如果没有找到您需要的酒店，请输入'显示更多'或'下一页'查看更多选项。"
                        
                        # 添加提示消息到对话
                        assistant_message = Message(role="assistant", content=options_message)
                        conversation.add_message(assistant_message)
                        db_service.save_message(conversation.id, assistant_message)
                        response = options_message
                        return
                    
                    # 尝试将用户输入解析为数字
                    selection = None
                    if user_input.isdigit():
                        selection = int(user_input)
                    else:
                        # 尝试从用户消息中提取酒店名称进行匹配
                        for i, hotel in enumerate(context["hotel_options"], 1):
                            if hotel.get("name") in user_input:
                                selection = i
                                break
                    
                    if selection and 1 <= selection <= len(context["hotel_options"]):
                        selected_hotel = context["hotel_options"][selection-1]
                        print(f"用户选择了酒店: {selected_hotel.get('name')}")
                        
                        # 获取选定酒店的详细信息
                        hotel_info = await gaode_mcp_service.search_hotel(selected_hotel.get("name"))
                        if hotel_info and not hotel_info.get("multiple_options", False):
                            # 保存详细酒店信息到上下文
                            # 创建新的上下文，只保留选定酒店的信息
                            # 清理所有与酒店选择相关的上下文信息
                            new_context = {
                                "hotel_info": hotel_info,
                                "hotel_name": selected_hotel.get("name"),  # 更新为精确的酒店名称
                                "waiting_for_hotel_selection": False  # 重置选择状态
                                # 不再保存hotel_options, all_hotels, total_hotels等信息
                            }
                            
                            # 替换原来的上下文，完全清理其他酒店信息
                            agent_service.conversation_contexts[conversation.id] = new_context
                            print(f"成功获取选定酒店的详细信息，已清理其他酒店信息: {hotel_info}")
                            
                            # 将酒店信息保存到对话元数据中，确保持久化
                            conversation.metadata["hotel_name"] = selected_hotel.get("name")
                            conversation.metadata["hotel_info"] = hotel_info
                            db_service.update_conversation(conversation)
                            
                            # 生成确认消息
                            confirmation = f"您已选择: {hotel_info.get('name')}\n地址: {hotel_info.get('formatted_address')}\n电话: {hotel_info.get('tel')}\n\n有什么可以帮您的吗？"
                            assistant_message = Message(role="assistant", content=confirmation)
                            conversation.add_message(assistant_message)
                            db_service.save_message(conversation.id, assistant_message)
                            response = confirmation
                except Exception as e:
                    print(f"处理酒店选择时出错: {str(e)}")
            
            # 检查用户是否在询问已选择酒店的电话或地址信息
            if context.get("hotel_info") and not context.get("waiting_for_hotel_selection"):
                is_asking_phone = any(keyword in user_input for keyword in ["电话", "联系方式", "联系电话", "联系"])
                is_asking_address = any(keyword in user_input for keyword in ["地址", "位置", "在哪里", "在哪"])
                
                if is_asking_phone:
                    # 用户询问电话信息
                    hotel_info = context["hotel_info"]
                    hotel_name = hotel_info.get("name", "")
                    tel = hotel_info.get("tel", "")
                    
                    if tel:
                        phone_message = f"您好，{hotel_name}的联系电话是：{tel}"
                    else:
                        phone_message = f"抱歉，我们暂时无法获取{hotel_name}的联系电话信息。您可以通过酒店官网或其他预订平台获取最新的联系方式。"
                    
                    # 添加电话信息到对话
                    assistant_message = Message(role="assistant", content=phone_message)
                    conversation.add_message(assistant_message)
                    db_service.save_message(conversation.id, assistant_message)
                    response = phone_message
                    
                elif is_asking_address:
                    # 用户询问地址信息
                    hotel_info = context["hotel_info"]
                    hotel_name = hotel_info.get("name", "")
                    address = hotel_info.get("formatted_address", "")
                    
                    if address:
                        address_message = f"您好，{hotel_name}的地址是：{address}"
                    else:
                        address_message = f"抱歉，我们暂时无法获取{hotel_name}的详细地址信息。"
                    
                    # 添加地址信息到对话
                    assistant_message = Message(role="assistant", content=address_message)
                    conversation.add_message(assistant_message)
                    db_service.save_message(conversation.id, assistant_message)
                    response = address_message
            
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
