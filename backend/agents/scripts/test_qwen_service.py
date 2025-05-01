#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
u6d4bu8bd5u901au4e49u5343u95eeu670du52a1

u6d4bu8bd5u901au4e49u5343u95eeu670du52a1u662fu5426u80fdu6b63u786eu52a0u8f7dAPIu5bc6u94a5
"""

import os
import sys
import asyncio

# u6dfbu52a0u9879u76eeu6839u76eeu5f55u5230Pythonu8defu5f84
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# u5bfcu5165u901au4e49u5343u95eeu670du52a1
from agent.app.services.qwen_text_service import QwenTextService

async def test_qwen_service():
    print("=== u6d4bu8bd5u901au4e49u5343u95eeu670du52a1 ===")
    
    # u521du59cbu5316u901au4e49u5343u95eeu670du52a1
    qwen_service = QwenTextService()
    
    # u68c0u67e5APIu5bc6u94a5u662fu5426u6b63u786eu52a0u8f7d
    if qwen_service.api_key:
        print(f"APIu5bc6u94a5u6210u529fu52a0u8f7d: {qwen_service.api_key[:10]}...")
    else:
        print("u8b66u544a: APIu5bc6u94a5u52a0u8f7du5931u8d25")
    
    # u68c0u67e5u5ba2u6237u7aefu662fu5426u521du59cbu5316u6210u529f
    if qwen_service.client:
        print("客户端初始化成功")
    else:
        print("警告: 客户端初始化失败")
    
    # u5982u679cu5ba2u6237u7aefu521du59cbu5316u6210u529fuff0cu6d4bu8bd5u4e00u4e2au7b80u5355u7684u8bf7u6c42
    if qwen_service.client:
        try:
            result = await qwen_service.analyze_text("这是一条测试消息", "请分析这条消息的情感")
            print(f"请求成功: {result}")
        except Exception as e:
            print(f"请求失败: {str(e)}")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_qwen_service())
