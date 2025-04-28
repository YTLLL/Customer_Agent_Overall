from langgraph.graph import StateGraph, END
from agent.app.models.conversation import Conversation, Message
from agent.app.services.qwen_text_service import QwenTextService
from agent.app.services.gaode_mcp_service import gaode_mcp_service
from agent.app.services.websocket_service import connection_manager
from typing import Optional, TypedDict, Literal
import json
import json
import re
from typing import Dict, Any


def safe_load_json(raw_text: str) -> Dict[str, Any]:
    """
    从包含 ```json 块的文本中安全提取 JSON 并解析成字典。
    如果解析失败，返回空字典。

    Args:
        raw_text (str): 原始模型返回的文本

    Returns:
        Dict[str, Any]: 提取后的 JSON 字典
    """
    try:
        # 正则提取出中间 {} 里的 JSON 块
        json_match = re.search(r'\{[\s\S]*\}', raw_text)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            # 如果没有 ``` 包裹，直接解析
            return json.loads(raw_text)
    except Exception as e:
        print(f"❌ safe_load_json 解析失败: {str(e)}")
        return {}
class ReasoningState(TypedDict):
    conversation: Conversation
    user_message: str
    hotel_name: Optional[str]
    hotel_info: Optional[dict]
    response: Optional[str]
    goal_achieved: bool
    is_refund_request: Optional[bool]
    refund_info_complete: Optional[bool]
    need_user_confirm_hotel: Optional[bool]
    booking_info_complete: Optional[bool]
    error: Optional[str]
    need_generate_response: Optional[bool]
    flow_type: Optional[str]
    need_hotel_info: Optional[str]
    need_analyze_booking: Optional[bool]
    need_analyze_refund: Optional[bool]

def print_state_graph(graph: StateGraph) -> None:
    """打印状态图的节点和边的结构"""
    print("\n=== State Graph Structure ===\n")

    # 打印节点
    print("Nodes:")
    print("-------")
    for node_name in graph.nodes:
        print(f"• {node_name}")

    # 打印边
    print("\nEdges:")
    print("-------")
    # 修改这部分来正确处理edges
    if hasattr(graph, '_edges'):  # 访问内部边结构
        for source, targets in graph._edges.items():
            for target in targets:
                print(f"• {source} -> {target}")
    else:
        print("(No direct edges)")

    # 打印条件边
    print("\nConditional Edges:")
    print("----------------")
    if hasattr(graph, '_conditional_edges'):
        for source, conditions in graph._conditional_edges.items():
            print(f"From: {source}")
            for condition, target in conditions.items():
                target_str = target if isinstance(target, str) else target.__name__
                print(f"• When '{condition}' -> {target_str}")
    else:
        print("(No conditional edges)")

    # 打印入口点
    print("\nEntry Point:")
    print("-----------")
    entry = graph.entry_point if hasattr(graph, 'entry_point') else "Unknown"
    print(f"• {entry}")

    # 打印流程图
    print("\n=== Graph Flow ===\n")
    print("extract_info")
    print("    ↓")
    print("check_goal ←←←←←←←←←")
    print("    ↓              ↑")
    print("    |              |")
    print("    ├─→ get_hotel_info")
    print("    |")
    print("    ├─→ analyze_booking_request ─→ generate_response")
    print("    |                                    ↑")
    print("    └─→ analyze_refund_request ─────────┘")
    print("                                         |")
    print("                                        END")


def check_state_graph(graph: StateGraph) -> None:
    """检查状态图的完整性"""
    print("\n=== State Graph Validation ===\n")

    # 检查是否有孤立节点
    all_nodes = set(graph.nodes.keys())
    connected_nodes = set()

    # 从入口点开始收集所有可达节点
    def collect_reachable_nodes(node):
        if node in connected_nodes:
            return
        connected_nodes.add(node)

        # 检查普通边
        if hasattr(graph, '_edges') and node in graph._edges:
            for target in graph._edges[node]:
                if isinstance(target, str) and target != "END":
                    collect_reachable_nodes(target)

        # 检查条件边
        if hasattr(graph, '_conditional_edges') and node in graph._conditional_edges:
            for condition_dict in graph._conditional_edges[node].values():
                if isinstance(condition_dict, str) and condition_dict != "END":
                    collect_reachable_nodes(condition_dict)

    # 从入口点开始检查
    if hasattr(graph, 'entry_point'):
        collect_reachable_nodes(graph.entry_point)

    # 输出结果
    unreachable = all_nodes - connected_nodes
    if unreachable:
        print("Warning: Found unreachable nodes:")
        for node in unreachable:
            print(f"• {node}")
    else:
        print("✓ All nodes are reachable")

    # 检查是否有终止路径
    has_end = False
    if hasattr(graph, '_edges'):
        for node, targets in graph._edges.items():
            if "END" in targets:
                has_end = True
                break

    if hasattr(graph, '_conditional_edges'):
        for node, conditions in graph._conditional_edges.items():
            if any(target == "END" for target in conditions.values()):
                has_end = True
                break

    if has_end:
        print("✓ Graph has valid termination paths")
    else:
        print("Warning: No termination paths found")


class ReasoningGraph:
    def __init__(self):
        self.qwen_service = QwenTextService()
        self.graph = self.compile_graph(self._build_graph())
        self.metadata = {}

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(ReasoningState)

        graph.add_node("extract_info", self._extract_info)
        graph.add_node("get_hotel_info", self._get_hotel_info)
        graph.add_node("analyze_booking_request", self._analyze_booking_request)
        graph.add_node("analyze_refund_request", self._analyze_refund_request)
        graph.add_node("generate_response", self._generate_response)
        graph.add_node("check_goal", self._check_goal)

        graph.add_edge("extract_info", "check_goal")
        graph.add_conditional_edges(
            "check_goal",
            self._route_on_goal,
            {
                "completed": "finalize_conversation",
                "need_generate_response": "generate_response",
                "need_hotel_info": "get_hotel_info",
                "need_analyze_booking": "analyze_booking_request",
                "need_analyze_refund": "analyze_refund_request",
            }
        )
        graph.add_node("finalize_conversation", self._finalize_conversation)
        graph.add_edge("finalize_conversation", END)
        # graph.add_edge("check_goal", END)
        graph.add_edge("get_hotel_info", "check_goal")
        graph.add_edge("analyze_booking_request", "generate_response")
        graph.add_edge("analyze_refund_request", "generate_response")
        graph.add_edge("generate_response", END)
        graph.set_entry_point("extract_info")
        print("building graph...")
        print("building graph... the graph is ", graph)
        # print_state_graph(graph)
        # check_state_graph(graph)
        return graph
    def compile_graph(self, graph):
        return graph.compile()

    def _route_on_goal(self, state: ReasoningState) -> Literal[
        "completed", "need_hotel_info", "need_generate_response", "need_analyze_booking", "need_analyze_refund"]:


        if state.get("goal_achieved"):
            return "completed"
        if state.get("need_generate_response"):
            print("need generate response")
            return "need_generate_response"
        if not state.get("hotel_info") and not state.get("need_user_confirm_hotel"):
            "need hotel info"
            return "need_hotel_info"
        if state.get("flow_type") == "booking" and not state.get("booking_info_complete"):
            return "need_analyze_booking"
        if state.get("flow_type") == "refund" and not state.get("refund_info_complete"):
            return "need_analyze_refund"
        return "need_generate_response"

    async def _extract_info(self, state: ReasoningState) -> ReasoningState:
        print("extract_info")
        user_message = state["user_message"]
        try:
            if not state.get("flow_type"):
                if any(keyword in user_message for keyword in ["退", "退款", "退订", "取消"]):
                    state["flow_type"] = "refund"
                    state["is_refund_request"] = True
                else:
                    state["flow_type"] = "booking"
                    state["is_refund_request"] = False

            prompt_hotel = f"请从以下用户消息中提取酒店名称。如果没有提到酒店，请返回空。\n用户消息：{user_message}"
            result_hotel = await self.qwen_service.analyze_text(user_message, prompt_hotel)
            hotel_name_extracted = result_hotel.get("raw_response", "").strip()
            if hotel_name_extracted and hotel_name_extracted.lower() != "空":
                state["hotel_name"] = hotel_name_extracted
                self.metadata["hotel_name"] = hotel_name_extracted
                state["conversation"].metadata["hotel_name"] = hotel_name_extracted
            else:
                state["hotel_name"] = None

            prompt_info = f"""请从以下用户消息中提取关键信息，并以**标准JSON格式**返回。

            用户消息：
            {user_message}

            需要提取以下字段（字段必须都有，如果没有请填null）：
            - destination: 目的地
            - check_in_date: 入住日期
            - guest_name: 客人姓名
            - hotel_tel: 酒店电话

            请只返回标准JSON，比如：
            {{
              "destination": "上海",
              "check_in_date": "2025-05-01",
              "guest_name": "张三",
              "hotel_tel": "021-12345678"
            }}

            如果某项信息未提及，填写 null，比如：
            {{
              "destination": "上海",
              "check_in_date": null,
              "guest_name": null,
              "hotel_tel": null
            }}
            """
            result_info = await self.qwen_service.analyze_text(user_message, prompt_info)
            print(result_info)


            raw_info = result_info.get("raw_response", "")
            info = safe_load_json(raw_info)
            print("info is ", info)
            try:
                print("metadata", self.metadata)
                if not self.metadata.get("check_in_date"):
                    self.metadata["check_in_date"] = info.get("check_in_date")
                if not self.metadata.get("guest_name"):
                    self.metadata["guest_name"] = info.get("guest_name")
                else:
                    print("the guest name is ", self.metadata["guest_name"])
                if not self.metadata.get("destination"):
                    self.metadata["destination"] = info.get("destination")
                    print("add destination")
                # 如果用户消息中提取到了酒店电话，直接写入 hotel_info 里
                if info.get("hotel_tel"):
                    state["hotel_info"] = {"tel": info.get("hotel_tel")}
                print("IM STILL THERE")
            except Exception as e:
                print("exception", str(e))
                pass
            return state
        except Exception as e:
            state["error"] = f"extract_info_error: {str(e)}"
            return state

    async def _get_hotel_info(self, state: ReasoningState) -> ReasoningState:
        print("get hotel info")
        hotel_name = state.get("hotel_name")
        state["need_generate_response"] = False
        if not hotel_name:
            # state["error"] = "没有提供酒店名称，无法检索酒店信息。"
            print("没有酒店名称")
            state["need_generate_response"] = True
            return state
        try:
            print("mcp")
            candidates = await gaode_mcp_service.search_hotels(hotel_name)
            print("candidates are ", candidates)
            if not candidates:
                state["hotel_info"] = None
                return state
            if len(candidates) == 1:
                detailed_info = await gaode_mcp_service.get_hotel_info(candidates[0]["id"])
                state["hotel_info"] = detailed_info
            else:
                user_id = state["conversation"].user_id
                options = [hotel["name"] for hotel in candidates]
                await connection_manager.broadcast_feedback(
                    user_id,
                    feedback_type="choose_hotel",
                    content=options,
                    metadata={"candidate_hotels": candidates}
                )
                state["need_user_confirm_hotel"] = True
                state["hotel_info"] = None
            return state
        except Exception as e:
            # print("get error", e)
            state["error"] = f"get_hotel_info_error: {str(e)}"
            return state

    async def _analyze_booking_request(self, state: ReasoningState) -> ReasoningState:
        print("analyze booking request")
        try:
            metadata = self.metadata or {}
            check_fields = ["hotel_name", "destination", "check_in_date", "hotel_info"]
            complete = all(metadata.get(field) or state.get(field) for field in check_fields)
            state["booking_info_complete"] = complete
            return state
        except Exception as e:
            state["error"] = f"analyze_booking_request_error: {str(e)}"
            return state

    async def _analyze_refund_request(self, state: ReasoningState) -> ReasoningState:
        print("analyze refund request")
        try:
            metadata = self.metadata or {}
            hotel_info = state.get("hotel_info") or metadata.get("hotel_info")
            check_tel = hotel_info and hotel_info.get("tel")
            complete = (state.get("hotel_name") or metadata.get("hotel_name")) and \
                       metadata.get("check_in_date") and \
                       metadata.get("guest_name") and \
                       check_tel
            state["refund_info_complete"] = complete
            return state
        except Exception as e:
            state["error"] = f"analyze_refund_request_error: {str(e)}"
            return state

    async def _finalize_conversation(self, state: ReasoningState) -> ReasoningState:
        print("finalize conversation")
        metadata = self.metadata
        try:
            flow_type = state.get("flow_type", "预订/退款")
            end_prompt = (
                f"你是酒店客服助手。\n"
                f"用户已经完整提供了{flow_type}所需的信息。\n"
                f"请生成一句礼貌、自然、专业的结束语，告诉用户我们正在为他处理。"
            )
            result = await self.qwen_service.analyze_text(end_prompt)
            end_message = result.get("raw_response", "感谢您的信息，我们正在为您处理。")

            state["response"] = end_message
            state["metadata_result"] = self.metadata  # 把收集到的所有信息返回
            # ✅ 如果是退款，再生成正式的 "向第三方平台申请退款" 文本
            refund_prompt_text = (
                f"你是客户服务专员，需要代替用户向第三方平台客服人员发起退款请求，请根据以下信息生成一封正式、完整的沟通文本：\n\n"
                f"酒店名称: {metadata.get('hotel_name', '未知酒店')}\n"
                f"入住日期: {metadata.get('check_in_date', '未知日期')}\n"
                f"客人姓名: {metadata.get('guest_name', '未知姓名')}\n\n"
                "要求：\n"
                "- 开场白，称呼对方客服人员\n"
                "- 简要说明用户因个人原因或不可抗力原因希望取消订单并申请退款\n"
                "- 核心正文需要表达清楚退款请求，并附上关键信息（如酒店名称、入住日期、客人姓名）\n"
                "- 语气正式、礼貌、专业，体现对平台服务的理解与感谢\n"
                "- 结尾希望对方审核处理，并表达感谢\n"
                "- 请生成完整的中文沟通内容（包括称呼、正文、结束语），不要只给出正文，不要添加解释说明。"
            )

            try:
                self.metadata["refund_prompt"] = refund_prompt_text
                print("✅ 退款申请正文生成完成！")
            except Exception as e:
                print(f"❌ 退款申请生成失败: {str(e)}")
                self.metadata["refund_prompt"] = "退款申请生成失败"


            return state

        except Exception as e:
            state["error"] = f"finalize_conversation_error: {str(e)}"
            return state

    async def _build_missing_info_prompt(self, missing_fields: list, intent: str) -> str:
        """根据缺失字段构建自然客服用语prompt"""
        fields_text = "、".join(missing_fields)
        prompt = (
            f"你是一个酒店客服，请用礼貌而自然的中文，向用户确认以下缺失的信息：{fields_text}。\n"
            f"用户当前意图是：{intent}。\n"
            f"请帮我生成一段友好、简洁的客服回复，不要直接列出字段，要自然引导用户补充这些信息。"
        )
        result = await self.qwen_service.analyze_text("", prompt)
        return result

    async def _generate_response(self, state: ReasoningState) -> ReasoningState:
        print("generate response")
        try:
            metadata = self.metadata or {}

            response_parts = []

            if state.get("error"):
                state["response"] = "抱歉，处理您的请求时遇到了问题，请稍后再试。"
                return state

            if state.get("flow_type") == "booking":
                missing = []
                if not (metadata.get("hotel_name") or state.get("hotel_name")):
                    missing.append("酒店名称")
                if not metadata.get("destination"):
                    missing.append("目的地")
                if not metadata.get("check_in_date"):
                    missing.append("入住日期")
                if not metadata.get("guest_name"):
                    missing.append("客人姓名")
                if not (metadata.get("hotel_info") or state.get("hotel_info")):
                    missing.append("酒店信息")
                if missing:
                    response_parts.append("为了帮您预订酒店，请提供以下信息：")
                    for field in missing:
                        response_parts.append(f"- {field}")
                    state["response"] = "\n".join(response_parts)
                    # state["response"] = await self._build_missing_info_prompt(missing, "订购酒店")
                    return state
                else:
                    state["response"] = "好的，您提供的信息已齐全，正在为您查询可预订酒店。"
                    return state

            if state.get("flow_type") == "refund":
                missing = []
                if not (metadata.get("hotel_name") or state.get("hotel_name")):
                    missing.append("酒店名称")
                if not metadata.get("check_in_date"):
                    missing.append("入住日期")
                if not metadata.get("guest_name"):
                    missing.append("退款人姓名")
                hotel_info = state.get("hotel_info") or metadata.get("hotel_info")
                if not hotel_info or not hotel_info.get("tel"):
                    missing.append("酒店电话")
                if missing:
                    response_parts.append("为了帮您处理退款，请提供以下信息：")

                    for field in missing:
                        response_parts.append(f"- {field}")
                    state["response"] = "\n".join(response_parts)
                    # state["response"] = self._build_missing_info_prompt(missing, "退款处理")
                    return state
                else:
                    state["response"] = "好的，您提供的退款信息已齐全，正在为您确认退订政策。"
                    return state

            state["response"] = "抱歉，我没能理解您的请求，请您详细描述。"

            return state

        except Exception as e:
            state["error"] = f"generate_response_error: {str(e)}"
            state["response"] = "抱歉，系统处理您的请求时遇到了错误。"
            return state

    async def _check_goal(self, state: ReasoningState) -> ReasoningState:
        print("check goal")
        try:
            metadata = self.metadata or {}

            if state.get("flow_type") == "booking":
                if (metadata.get("hotel_name") or state.get("hotel_name")) and \
                   metadata.get("destination") and metadata.get("check_in_date") and \
                   (metadata.get("hotel_info") or state.get("hotel_info")):
                    state["goal_achieved"] = True
                    print("goal achieved")
                else:

                    state["need_generate_response"] = True
                    state["goal_achieved"] = False
                    return state
            elif state.get("flow_type") == "refund":
                hotel_info = state.get("hotel_info") or metadata.get("hotel_info")
                if (metadata.get("hotel_name") or state.get("hotel_name")) and \
                   metadata.get("check_in_date") and metadata.get("guest_name") and \
                   hotel_info and hotel_info.get("tel"):
                    state["goal_achieved"] = True
                else:
                    state["goal_achieved"] = False

            else:
                state["goal_achieved"] = False

            return state

        except Exception as e:
            state["error"] = f"check_goal_error: {str(e)}"
            state["goal_achieved"] = False
            return state

    def print_graph(self):
        for node_name, node_obj in self.graph._nodes.items():
            print(f"node {node_name}: {node_obj.fn}")

    async def process_request(self, conversation: Conversation, user_message: str) -> str:
        initial_state: ReasoningState = {
            "conversation": conversation,
            "user_message": user_message,
            "hotel_name": None,
            "hotel_info": None,
            "response": None,
            "goal_achieved": False,
            "is_refund_request": None,
            "refund_info_complete": None,
            "booking_info_complete": None,
            "need_user_confirm_hotel": None,
            "error": None,
            "flow_type": None,
        }
        try:
            # 运行推理图
            final_state = await self.graph.ainvoke(initial_state)
            for key, value in self.metadata.items():
                if value is not None:
                    conversation.metadata[key] = value
            # 检查是否有错误
            if final_state.get("error"):
                return f"抱歉，处理您的请求时遇到了问题: {final_state['error']}"

            # 返回生成的回复
            return final_state.get("response", "抱歉，无法生成回复")
        except Exception as e:
            # 处理推理图执行过程中的异常
            return f"抱歉，系统处理您的请求时遇到了技术问题: {str(e)}"
