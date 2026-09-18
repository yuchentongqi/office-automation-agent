# agent/graph.py
"""Supervisor + 子 Agent 工作流"""
from langgraph.graph import StateGraph, START, END

from agent.nodes import (
    AgentState,
    supervisor,
    route_by_intent,
    calendar_node,
    message_node,
    email_node,
    report_node,
    chitchat_node,
    review_node,
)


def build_graph():
    builder = StateGraph(AgentState)

    # 注册节点
    builder.add_node("supervisor", supervisor)
    builder.add_node("calendar", calendar_node)
    builder.add_node("message", message_node)
    builder.add_node("email", email_node)
    builder.add_node("report", report_node)
    builder.add_node("chitchat", chitchat_node)
    builder.add_node("review", review_node)

    # 入口：先走主管
    builder.add_edge(START, "supervisor")

    # 主管判断意图后，路由到对应节点
    builder.add_conditional_edges(
        "supervisor",
        route_by_intent,
        {
            "日历": "calendar",
            "消息": "message",
            "邮件": "email",
            "任务": "email",
            "周报": "report",
            "闲聊": "chitchat",
        },
    )

    # 所有专业节点处理完，都进审核
    for node in ["calendar", "message", "email", "report", "chitchat"]:
        builder.add_edge(node, "review")

    # 审核完结束
    builder.add_edge("review", END)

    return builder.compile()


if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    graph = build_graph()

    test_questions = [
        "生成本周周报",
        "看看我最近的任务",
        "今天有什么日程安排？",
    ]

    for q in test_questions:
        print("\n" + "=" * 55)
        print(f"用户：{q}")
        result = graph.invoke({
            "messages": [HumanMessage(content=q)],
            "intent": "",
            "answer": "",
            "review_passed": False,
        })
        print(f"意图：{result['intent']}")
        print(f"回复：{result['answer']}")