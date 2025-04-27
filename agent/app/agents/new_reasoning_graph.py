from langgraph.graph import StateGraph, END
from agent.app.models.conversation import Conversation, Message
from agent.app.services.qwen_text_service import QwenTextService
from agent.app.services.gaode_mcp_service import gaode_mcp_service
from agent.app.services.websocket_service import connection_manager
from typing import Optional, TypedDict, Literal
import json

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
    flow_type: Optional[str]


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
                "completed": END,
                "need_hotel_info": "get_hotel_info",
                "need_generate_response": "generate_response",
                "need_analyze_booking": "analyze_booking_request",
                "need_analyze_refund": "analyze_refund_request",
            }
        )
        # graph.add_edge("check_goal", END)
        graph.add_edge("get_hotel_info", "check_goal")
        graph.add_edge("analyze_booking_request", "generate_response")
        graph.add_edge("analyze_refund_request", "generate_response")
        graph.add_edge("generate_response", END)
        graph.set_entry_point("extract_info")
        print("building graph...")
        print("building graph... the graph is ", graph)
        for node in graph.nodes:
            if not callable(graph.nodes[node]):
                raise RuntimeError(f"节点 {node} 不可调用: {graph.nodes[node]}")
            else:
                print("working")
        # print_state_graph(graph)
        # check_state_graph(graph)
        return graph
    def compile_graph(self, graph):
        return graph.compile()

    def _route_on_goal(self, state: ReasoningState) -> Literal[
        "completed", "need_hotel_info", "need_generate_response", "need_analyze_booking", "need_analyze_refund"]:
        if state.get("goal_achieved"):
            return "completed"
        if not state.get("hotel_info") and not state.get("need_user_confirm_hotel"):
            return "need_hotel_info"
        if state.get("flow_type") == "booking" and not state.get("booking_info_complete"):
            return "need_analyze_booking"
        if state.get("flow_type") == "refund" and not state.get("refund_info_complete"):
            return "need_analyze_refund"
        return "need_generate_response"

    async def _extract_info(self, state: ReasoningState) -> ReasoningState:
        user_message = state["user_message"]
        try:
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
            else:
                state["hotel_name"] = None

            prompt_info = f"请从以下用户消息中提取信息：\n用户消息：{user_message}\n需要提取：destination, check_in_date, guest_name, hotel_tel"
            result_info = await self.qwen_service.analyze_text(user_message, prompt_info)
            raw_info = result_info.get("raw_response", "")
            try:
                info = json.loads(raw_info)
                metadata = state["conversation"].metadata
                metadata["destination"] = info.get("destination")
                metadata["check_in_date"] = info.get("check_in_date")
                metadata["guest_name"] = info.get("guest_name")
                # 如果用户消息中提取到了酒店电话，直接写入 hotel_info 里
                if info.get("hotel_tel"):
                    state["hotel_info"] = {"tel": info.get("hotel_tel")}
            except Exception:
                pass
            return state
        except Exception as e:
            state["error"] = f"extract_info_error: {str(e)}"
            return state

    async def _get_hotel_info(self, state: ReasoningState) -> ReasoningState:
        hotel_name = state.get("hotel_name")
        if not hotel_name:
            state["error"] = "没有提供酒店名称，无法检索酒店信息。"
            return state
        try:
            candidates = await gaode_mcp_service.search_hotels(hotel_name)
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
            state["error"] = f"get_hotel_info_error: {str(e)}"
            return state

    async def _analyze_booking_request(self, state: ReasoningState) -> ReasoningState:
        try:
            metadata = state["conversation"].metadata or {}
            check_fields = ["hotel_name", "destination", "check_in_date", "hotel_info"]
            complete = all(metadata.get(field) or state.get(field) for field in check_fields)
            state["booking_info_complete"] = complete
            return state
        except Exception as e:
            state["error"] = f"analyze_booking_request_error: {str(e)}"
            return state

    async def _analyze_refund_request(self, state: ReasoningState) -> ReasoningState:
        try:
            metadata = state["conversation"].metadata or {}
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

    async def _generate_response(self, state: ReasoningState) -> ReasoningState:
        try:
            metadata = state["conversation"].metadata or {}
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
                if not (metadata.get("hotel_info") or state.get("hotel_info")):
                    missing.append("酒店信息")
                if missing:
                    response_parts.append("为了帮您预订酒店，请提供以下信息：")
                    for field in missing:
                        response_parts.append(f"- {field}")
                    state["response"] = "\n".join(response_parts)
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
                    missing.append("入住人姓名")
                hotel_info = state.get("hotel_info") or metadata.get("hotel_info")
                if not hotel_info or not hotel_info.get("tel"):
                    missing.append("酒店电话")
                if missing:
                    response_parts.append("为了帮您处理退款，请提供以下信息：")
                    for field in missing:
                        response_parts.append(f"- {field}")
                    state["response"] = "\n".join(response_parts)
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
        try:
            metadata = state["conversation"].metadata or {}

            if state.get("flow_type") == "booking":
                if (metadata.get("hotel_name") or state.get("hotel_name")) and \
                   metadata.get("destination") and metadata.get("check_in_date") and \
                   (metadata.get("hotel_info") or state.get("hotel_info")):
                    state["goal_achieved"] = True
                else:
                    state["goal_achieved"] = False

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
            # print("the graph is ", self.graph)
            # print("graph is", self.graph)
            graph = self._build_graph()
            print("Graph nodes:", graph.nodes)  # Check all nodes exist
            print("Graph edges:", graph.edges)  # Check edges exist

            # Verify initial state
            print("Initial state keys:", initial_state.keys())

            result = graph.invoke(initial_state)
        except Exception as e:
            print("errorsdfs:", e)
        response = result.get("response", "处理失败")

        conversation.messages.append(
            Message(role="assistant", content=response)
        )

        return response
