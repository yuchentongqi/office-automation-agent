# agent/nodes.py
"""Supervisor + 子 Agent 节点"""
import os
from typing import Annotated, TypedDict
from operator import add

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from agent.report_tools import generate_weekly_report

from agent.tools import (
    create_calendar_event,
    list_calendar_events,
    send_feishu_message,
    get_current_time,
)

from agent.email_tools import (
    list_emails,
    read_email,
    search_emails,
    send_email,
)

from agent.task_tools import (
    extract_tasks_from_email,
    list_tasks,
    complete_task,
)

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.7-flash")
BASE_URL = os.getenv("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
API_KEY = os.getenv("DASHSCOPE_API_KEY")


def get_llm():
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0,
    )


# ============ 状态 ============
class AgentState(TypedDict):
    messages: Annotated[list, add]
    intent: str
    answer: str
    review_passed: bool


# ============ Supervisor：意图识别 ============
SUPERVISOR_PROMPT = """你是办公自动化助手的主管。判断用户的需求属于哪一类，只返回一个词：

- 日历：创建日程、查询日程、安排会议、看今天/明天有什么安排
- 消息：发飞书消息给某人、通知某人
- 邮件：查看邮件、搜索邮件、发送邮件、读邮件
- 任务：查看任务清单、提取任务、标记任务完成、待办事项
- 周报：生成本周周报、工作总结、汇报
- 闲聊：打招呼、问你是谁、与办公无关的对话

用户问题：{question}

只返回：日历 / 消息 / 邮件 / 任务 / 周报 / 闲聊"""


def supervisor(state: AgentState):
    question = state["messages"][-1].content
    llm = get_llm()
    result = llm.invoke([HumanMessage(content=SUPERVISOR_PROMPT.format(question=question))])
    raw = result.content.strip()

    intent = "闲聊"
    for valid in ["日历", "消息", "邮件", "任务", "周报", "闲聊"]:
        if valid in raw:
            intent = valid
            break

    print(f"[主管] 意图：{intent}")
    return {"intent": intent}


def route_by_intent(state: AgentState):
    return state["intent"]


# ============ 日历 Agent ============
_CALENDAR_AGENT = None


def get_calendar_agent():
    global _CALENDAR_AGENT
    if _CALENDAR_AGENT is None:
        _CALENDAR_AGENT = create_react_agent(
            get_llm(),
            tools=[create_calendar_event, list_calendar_events, get_current_time],
            prompt=(
                "你是日历管理助手。用户要创建日程或查询日程时，调用工具完成。\n"
                "重要规则：\n"
                "1. 用户说'明天'、'下周一'等相对时间时，必须先调用 get_current_time 获取当前日期\n"
                "2. 创建日程时，时间格式必须是 'YYYY-MM-DD HH:MM:SS'\n"
                "3. 如果用户没给结束时间，默认持续 1 小时\n"
                "4. 回复要简洁，确认创建或查询的结果"
            ),
        )
    return _CALENDAR_AGENT


def calendar_node(state: AgentState):
    agent = get_calendar_agent()
    result = agent.invoke({"messages": state["messages"]})
    return {"answer": result["messages"][-1].content}


# ============ 消息 Agent ============
_MESSAGE_AGENT = None


def get_message_agent():
    global _MESSAGE_AGENT
    if _MESSAGE_AGENT is None:
        _MESSAGE_AGENT = create_react_agent(
            get_llm(),
            tools=[send_feishu_message],
            prompt=(
                "你是飞书消息助手。用户要发消息时，调用 send_feishu_message 工具。\n"
                "重要：open_id 是用户的唯一标识。如果用户没有提供 open_id，"
                "请礼貌地告诉用户需要提供 open_id 才能发送消息。"
            ),
        )
    return _MESSAGE_AGENT


def message_node(state: AgentState):
    agent = get_message_agent()
    result = agent.invoke({"messages": state["messages"]})
    return {"answer": result["messages"][-1].content}


# ============ 闲聊 ============
def chitchat_node(state: AgentState):
    llm = get_llm()
    question = state["messages"][-1].content
    result = llm.invoke([
        SystemMessage(content=(
            "你是办公自动化助手。简短回应用户的打招呼或闲聊，"
            "并引导他们使用核心功能：创建日程、查询日程、发送飞书消息。"
        )),
        HumanMessage(content=question),
    ])
    return {"answer": result.content}

# ============ 邮件 Agent ============
_EMAIL_AGENT = None


def get_email_agent():
    global _EMAIL_AGENT
    if _EMAIL_AGENT is None:
        _EMAIL_AGENT = create_react_agent(
            get_llm(),
            tools=[
                list_emails, read_email, search_emails, send_email,
                extract_tasks_from_email, list_tasks, complete_task,
            ],
                       prompt=(
                "你是邮件管理助手。用户要查看、搜索、读取、发送邮件或管理任务时，调用对应工具。\n"
                "重要规则：\n"
                "1. 用户想看邮件列表时，调用 list_emails\n"
                "2. 用户想找特定邮件时，调用 search_emails\n"
                "3. 用户想读某封邮件时，先用 list_emails 或 search_emails 拿到 ID，再调用 read_email\n"
                "4. 用户要发邮件时，调用 send_email\n"
                "5. 用户要从邮件提取任务时，先 read_email 拿到主题和正文，再调用 extract_tasks_from_email\n"
                "6. 用户想查看任务清单时，调用 list_tasks\n"
                "7. 用户要标记任务完成时，调用 complete_task\n"
                "8. 回复要简洁，把关键信息呈现给用户"
            ),
        )
    return _EMAIL_AGENT


def email_node(state: AgentState):
    agent = get_email_agent()
    result = agent.invoke({"messages": state["messages"]})
    return {"answer": result["messages"][-1].content}    


# ============ 审核 ============
REVIEW_PROMPT = """你是回复审核员。检查下面的助手回复是否有严重问题：

用户问题：{question}
助手回复：{answer}

只在出现以下明确问题时判不通过：
1. 编造了工具未返回的信息（如虚构的日程 ID、时间）
2. 做出了不恰当的承诺
3. 答非所问

注意：回复中的具体时间、日程信息通常来自飞书 API，不要仅因出现具体信息就判为编造。

如果没有问题，只返回：通过
如果有问题，返回：不通过 | 原因

只返回一行。"""

# ============ 周报 Agent ============
_REPORT_AGENT = None


def get_report_agent():
    global _REPORT_AGENT
    if _REPORT_AGENT is None:
        _REPORT_AGENT = create_react_agent(
            get_llm(),
            tools=[generate_weekly_report],
            prompt=(
                "你是周报生成助手。用户要生成周报、工作总结或汇报时，"
                "调用 generate_weekly_report 工具。工具会自动收集本周日程和任务。"
                "调用后把报告内容完整呈现给用户。"
            ),
        )
    return _REPORT_AGENT


def report_node(state: AgentState):
    agent = get_report_agent()
    result = agent.invoke({"messages": state["messages"]})
    return {"answer": result["messages"][-1].content}


def review_node(state: AgentState):
    question = state["messages"][-1].content
    answer = state["answer"]

    llm = get_llm()
    result = llm.invoke([
        HumanMessage(content=REVIEW_PROMPT.format(question=question, answer=answer))
    ])
    verdict = result.content.strip()

    passed = verdict.startswith("通过")
    print(f"[审核] {'通过' if passed else verdict[:60]}")

    return {
        "review_passed": passed,
        "messages": [AIMessage(content=answer)],
    }