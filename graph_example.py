from langgraph.graph import StateGraph
from langgraph.graph import StateGraph, END
from agent.app.models.conversation import Conversation, Message
from agent.app.services.qwen_text_service import QwenTextService
from agent.app.services.gaode_mcp_service import gaode_mcp_service
from agent.app.services.websocket_service import connection_manager
from typing import Optional, TypedDict, Literal
import json
# 不再需要 START 和 END，直接写 "__start__" 和 "__end__"

# Create the structure of the schema for the graph
from typing_extensions import TypedDict

class MyGraphState(TypedDict):
    count: int
    msg: str

# Define your node
def counter(state: MyGraphState):
    state["count"] += 1
    state["msg"] = f"Counter function has been called {state['count']} time(s)"
    return state

# Create an instance of StateGraph with the structure of MyGraphState
workflow = StateGraph(MyGraphState)

# Add nodes
workflow.add_node("Node1", counter)
workflow.add_node("Node2", counter)
workflow.add_node("Node3", counter)

# Add edges
workflow.add_edge("__start__", "Node1")
workflow.add_edge("Node1", "Node2")
workflow.add_edge("Node2", "Node3")
workflow.add_edge("Node3", "__end__")

# Compile the workflow
app = workflow.compile()

# # Visualize your graph (optional)
# from IPython.display import Image, display
# png = app.get_graph().draw_mermaid_png()
# display(Image(png))

# Run the workflow
app.invoke({"count": 0, "msg": "hello"})

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
# 测试代码
def a(state: ReasoningState) -> ReasoningState:
    pass
def b(state: ReasoningState) -> ReasoningState:
    pass
def c(state: ReasoningState) -> ReasoningState:
    pass
def d(state: ReasoningState) -> ReasoningState:
    pass
def e(state: ReasoningState) -> ReasoningState:
    pass
def f(state: ReasoningState) -> ReasoningState:
    pass
graph = StateGraph(ReasoningState)
graph.add_node("a", a)
graph.add_node("b", b)
graph.add_node("c", c)
graph.add_node("d", d)
graph.add_node("e", e)
graph.add_node("f", f)
graph.add_edge("a", "b")


def _route_on_goal(state: ReasoningState) -> Literal[
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
graph.add_conditional_edges(
    "b",
    _route_on_goal,
    {
        "completed": END,
        "need_hotel_info": "d",
        "need_generate_response": "f",
        "need_analyze_booking": "c",
        "need_analyze_refund": "e",
    }
)
graph.add_edge("d", "b")
graph.add_edge("c", "f")
graph.add_edge("e", "f")
graph.add_edge("f", END)
graph.set_entry_point("a")
print(graph.compile().invoke({"conversation": {}, "user_message": "test"}))
# 应该能正常编译
assert graph.compile().invoke({"conversation": {}, "user_message": "test"})