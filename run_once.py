import requests
import time

API_BASE = "http://localhost:8000/api"
USER_ID = "test_user_001"
CHANNEL = "terminal"
HOTEL_NAME = "汉庭酒店"
phone_number = "电话号码"
name = "haohao"
personal_info = "我想退款 酒店太好了"

def start_conversation():
    text = input("👤 你：")
    res = requests.post(f"{API_BASE}/callingconversation", json={
        "user_id": USER_ID,
        "message": text,
        # "channel": CHANNEL
    })
    if res.status_code != 200:
        print("❌ 启动对话失败：", res.text)
        exit()
    data = res.json()
    return data["conversation_id"], data["messages"]

def postHotelInfo():
    res = requests.post(f"{API_BASE}/generate_prompt", json={
        "user_id":USER_ID,
        "flight"
        "phone_number":phone_number,
        "name":name,
        "personal_info":personal_info
    })
    if res.status_code != 200:
        print("❌ 发送失败：", res.text)
    else:
        print("成功")
def continue_conversation(conversation_id):
    while True:
        text = input("👤 你：")
        if text.lower() in ["exit", "quit"]:
            print("🛑 正在结束对话并生成总结...\n")
            res = requests.post(f"{API_BASE}/callingconversation/{conversation_id}/end")
            print("📄 总结：", res.json().get("summary", "总结失败"))
            break

        res = requests.post(f"{API_BASE}/callingconversation", json={
            "user_id": USER_ID,
            "message": text,
            # "channel": CHANNEL
        })
        if res.status_code != 200:
            print("❌ 发送失败：", res.text)
            continue

        print("⏳ 生成中，请稍候...")
        # 等待后台生成完（你也可以改成轮询）
        time.sleep(1.5)

        # 获取对话详情
        detail = requests.get(f"{API_BASE}/callingconversation/{conversation_id}")
        if detail.status_code == 200:
            last_msg = detail.json()["messages"][-1]
            if last_msg["role"] == "assistant":
                print(f"🤖 助手：{last_msg['content']}\n")
            else:
                print("🤖 暂无助手回复\n")
        else:
            print("❌ 获取对话失败")

if __name__ == "__main__":
    # postHotelInfo()
    print("start")
    conv_id, msgs = start_conversation()
    print("continue")
    last_assistant = next((m["content"] for m in reversed(msgs) if m["role"] == "assistant"), None)
    if last_assistant:
        print(f"🤖 助手：{last_assistant}\n")
    continue_conversation(conv_id)