import asyncio
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""推理图模块

这个模块实现了推理代理功能，负责处理用户的酒店服务请求。
使用顺序处理流程实现推理，便于后期与其他模块集成。
"""

import os
import json
import logging
import re
from enum import Enum
from typing import Dict, List, Literal, TypedDict, Optional, Union, Any, Tuple

from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from agent.app.models.conversation import Conversation, Message
from agent.app.agents.reasoning_graph import ReasoningGraph
from agent.app.models.conversation import Conversation, Message
from agent.app.services.qwen_text_service import QwenTextService
from agent.app.utils.helpers import extract_hotel_name, format_hotel_info
from agent.app.services.gaode_mcp_service import gaode_mcp_service
from agent.app.services.websocket_service import connection_manager
async def main():
    reasoning_graph = ReasoningGraph()
    result = await reasoning_graph.extract_info_with_api("你好 我订广州汉庭酒店 电话号码1234567890")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
