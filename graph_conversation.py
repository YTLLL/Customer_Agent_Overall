import asyncio
from agent.app.models.conversation import Conversation, Message
from agent.app.agents.new_reasoning_graph import ReasoningGraph  # 你的 ReasoningGraph 文件路径
import sys
from agent.app.services.db_service import DBService
from motor.motor_asyncio import AsyncIOMotorClient

# 初始化 MongoDB 连接（只要做一次）
client = AsyncIOMotorClient("mongodb://localhost:27017")  # 或者你的 MongoDB 地址
db = client["hotel_db"]
refund_prompt_collection = db["refund_prompts"]

async def save_refund_prompt(user_id: str, refund_prompt: str):
    """保存 refund prompt 到 MongoDB"""
    document = {
        "user_id": user_id,
        "refund_prompt": refund_prompt,
    }
    await refund_prompt_collection.insert_one(document)

async def interactive_reasoning():
    # 初始化对话对象
    user_id = "test_user_001"
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
            print(reasoning_graph.metadata)
            db_service = DBService()
            db_service.save_conversation(conversation)
            print("👋 结束对话")
            # 可选：打印 summary 和 refund_prompt
            if conversation.metadata.get("summary"):
                print("\n📝 当前对话总结：")
                print(conversation.metadata["summary"])

            if reasoning_graph.metadata.get("refund_prompt"):
                print("\n🏷️ 当前退款提示：")
                refund_prompt = conversation.metadata["refund_prompt"]
                await save_refund_prompt(user_id, refund_prompt)
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




# 运行
if __name__ == "__main__":
    asyncio.run(interactive_reasoning())
