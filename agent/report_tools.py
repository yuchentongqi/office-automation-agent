# agent/report_tools.py
"""周报生成工具"""
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from agent.feishu_api import list_events
from agent.task_tools import _conn

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.7-flash")
BASE_URL = os.getenv("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
API_KEY = os.getenv("DASHSCOPE_API_KEY")


def _get_llm():
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0,
    )


REPORT_PROMPT = """你是一位助理，请根据下面的数据生成一份简洁的周报。

时间范围：{start_date} 至 {end_date}

本周日程：
{events_text}

本周任务：
{tasks_text}

要求：
1. 使用 Markdown 格式
2. 包含三个部分：本周概要、日程回顾、任务进展
3. 语言简洁专业，200 字以内
4. 直接输出正文，不要开场白，不要一级标题
"""


@tool
def generate_weekly_report() -> str:
    """生成本周工作周报。收集本周的日程和任务，汇总成 Markdown 报告并保存。"""
    # 计算本周范围（周一到周日）
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    start_str = monday.strftime("%Y-%m-%d 00:00:00")
    end_str = sunday.strftime("%Y-%m-%d 23:59:59")

    # 收集日程
    try:
        events = list_events(start_str, end_str)
        if events:
            events_text = "\n".join(
                f"- {e['summary']}（{e['start']} ~ {e['end']}）" for e in events
            )
        else:
            events_text = "（本周无日程）"
    except Exception as e:
        events_text = f"（获取日程失败：{e}）"

    # 收集任务
    conn = _conn()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT title, due_date, status FROM tasks ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    if rows:
        tasks_text = "\n".join(
            f"- {r['title']}" + (f"（截止 {r['due_date']}）" if r["due_date"] else "")
            + f" - {r['status']}"
            for r in rows
        )
    else:
        tasks_text = "（暂无任务）"

    # 调 LLM 生成报告
    llm = _get_llm()
    prompt = REPORT_PROMPT.format(
        start_date=monday.strftime("%Y-%m-%d"),
        end_date=sunday.strftime("%Y-%m-%d"),
        events_text=events_text,
        tasks_text=tasks_text,
    )
    result = llm.invoke([HumanMessage(content=prompt)])
    report_body = result.content.strip()

    # 保存文件
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filepath = REPORTS_DIR / f"weekly_{timestamp}.md"
    full_report = (
        f"# 工作周报（{monday.strftime('%Y-%m-%d')} ~ {sunday.strftime('%Y-%m-%d')}）\n\n"
        f"{report_body}\n"
    )
    filepath.write_text(full_report, encoding="utf-8")

    return (
        f"✅ 周报已生成并保存到 {filepath}\n\n"
        f"---\n\n{full_report}"
    )


ALL_REPORT_TOOLS = [generate_weekly_report]