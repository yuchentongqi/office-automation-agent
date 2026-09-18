# app.py
import gradio as gr
from langchain_core.messages import HumanMessage, AIMessage

from agent.graph import build_graph

print("正在初始化办公自动化 Agent...")
graph = build_graph()
print("Agent 就绪")

# 记忆窗口：保留最近 3 轮对话
MAX_HISTORY_TURNS = 3

last_state = {"intent": ""}


def respond(message, chat_history):
    if not message.strip():
        return "", chat_history, last_state["intent"]

    # 1. 从 chat_history 里取最近 N 轮，转成 LangChain 消息
    recent = chat_history[-(MAX_HISTORY_TURNS * 2):]
    history_msgs = []
    for m in recent:
        if m["role"] == "user":
            history_msgs.append(HumanMessage(content=m["content"]))
        else:
            history_msgs.append(AIMessage(content=m["content"]))

    # 2. 加上当前这条消息
    history_msgs.append(HumanMessage(content=message))

    # 3. 传给工作流
    result = graph.invoke({
        "messages": history_msgs,
        "intent": "",
        "answer": "",
        "review_passed": False,
    })

    answer = result["answer"]
    intent = result["intent"]
    last_state["intent"] = intent

    chat_history = chat_history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer},
    ]
    return "", chat_history, intent


with gr.Blocks(title="办公自动化 Agent") as demo:
    gr.Markdown("# 办公自动化 Agent")
    gr.Markdown("Supervisor 调度：日历管理 / 飞书消息 / 邮件处理 / 任务管理 / 周报生成")

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=450, label="对话")
            msg = gr.Textbox(
                placeholder="输入问题，按回车发送...",
                label="你的问题",
                lines=1,
            )
            with gr.Row():
                send_btn = gr.Button("发送", variant="primary")
                clear_btn = gr.Button("清空")

        with gr.Column(scale=1):
            gr.Markdown("### 意图识别")
            intent_box = gr.Textbox(label="当前意图", interactive=False)

            gr.Markdown("### 试试这些问题")
            gr.Examples(
                examples=[
                    "看看我最近的邮件",
                    "今天有什么日程安排？",
                    "看看我最近的任务",
                    "生成本周周报",
                ],
                inputs=msg,
            )

    msg.submit(respond, [msg, chatbot], [msg, chatbot, intent_box])
    send_btn.click(respond, [msg, chatbot], [msg, chatbot, intent_box])
    clear_btn.click(lambda: (None, "", ""), None, [chatbot, intent_box, msg])


if __name__ == "__main__":
    demo.launch()