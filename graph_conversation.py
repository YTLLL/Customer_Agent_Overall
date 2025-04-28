import asyncio
from agent.app.models.conversation import Conversation, Message
from agent.app.agents.new_reasoning_graph import ReasoningGraph  # 你的 ReasoningGraph 文件路径
import sys


async def interactive_reasoning():
    # 初始化对话对象
    conversation = Conversation(
        user_id="test_user_001",
        channel="test_channel",  # ✅ 补上这个字段
        messages=[],
        metadata={}
    )

    # 初始化 ReasoningGraph
    reasoning_graph = ReasoningGraph()

    print("💬 ReasoningGraph 多轮对话测试开始！（输入 'exit' 退出）")

    while True:
        # 用户输入
        user_input = input("\n👤 你：")
        if user_input.strip().lower() == "exit":
            print("👋 结束对话")
            break

        # 将用户输入添加到对话历史
        conversation.messages.append(
            Message(role="user", content=user_input)
        )

        # 调用 ReasoningGraph 推理
        try:
            response = await reasoning_graph.process_request(conversation, user_input)
        except Exception as e:
            print(f"❌ 推理出错: {str(e)}")
            sys.exit(1)

        # 显示助手回复
        print(f"\n🤖 助手：{response}")

        # 可选：打印 summary 和 refund_prompt
        if conversation.metadata.get("summary"):
            print("\n📝 当前对话总结：")
            print(conversation.metadata["summary"])

        if conversation.metadata.get("refund_prompt"):
            print("\n🏷️ 当前退款提示：")
            print(conversation.metadata["refund_prompt"])


# 运行
if __name__ == "__main__":
    asyncio.run(interactive_reasoning())
