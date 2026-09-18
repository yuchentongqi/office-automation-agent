# agent/task_tools.py
"""任务提取与管理工具"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "tasks.db"

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


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


EXTRACT_PROMPT = """从下面的邮件内容中提取待办事项。

邮件主题：{subject}
邮件正文：
{body}

要求：
1. 只提取明确的待办事项（有具体要做的事）
2. 每条任务格式：任务标题 | 截止日期（如有，格式 YYYY-MM-DD；没有写"无"）
3. 一行一条，不要编号，不要其他解释
4. 如果没有待办事项，只返回：无任务

示例输出：
提交季度报告 | 2026-09-20
预约下周的会议室 | 无
回复客户邮件 | 2026-09-18
"""


@tool
def extract_tasks_from_email(subject: str, body: str) -> str:
    """从邮件内容中提取待办事项，并保存到任务列表。

    Args:
        subject: 邮件主题
        body: 邮件正文
    """
    print(f"[任务提取] 开始处理：{subject}")

    llm = _get_llm()
    prompt = EXTRACT_PROMPT.format(subject=subject, body=body)
    print("[任务提取] 调用 LLM...")

    result = llm.invoke([HumanMessage(content=prompt)])
    raw = result.content.strip()
    print(f"[任务提取] LLM 返回：{raw[:200]}")

    if "无任务" in raw or not raw:
        return "这封邮件中没有提取到待办事项。"

    # 解析每行任务，更宽松：找含 | 的行，或者整行当作标题
    lines = []
    for line in raw.splitlines():
        line = line.strip().lstrip("0123456789.-、) ").strip()
        if not line:
            continue
        if "|" in line:
            parts = [p.strip() for p in line.split("|", 1)]
            title = parts[0]
            due = parts[1] if len(parts) > 1 and parts[1] not in ("无", "") else None
        else:
            title = line
            due = None
        if title and title not in ("无任务", "无"):
            lines.append((title, due))

    if not lines:
        return f"未能解析出任务。原始输出：\n{raw}"

    conn = _conn()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    saved = []

    for title, due_date in lines:
        cur.execute(
            "INSERT INTO tasks (title, source_email, due_date, created_at) VALUES (?, ?, ?, ?)",
            (title, subject, due_date, now),
        )
        saved.append(f"- {title}" + (f"（截止 {due_date}）" if due_date else ""))

    conn.commit()
    conn.close()

    return f"已提取 {len(saved)} 条任务并保存：\n" + "\n".join(saved)

@tool
def list_tasks(status: str = "待办") -> str:
    """列出任务清单。

    Args:
        status: 任务状态筛选，可选 "待办" / "已完成" / "全部"，默认 "待办"
    """
    conn = _conn()
    cur = conn.cursor()

    if status == "全部":
        rows = cur.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    else:
        rows = cur.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()

    conn.close()

    if not rows:
        return f"没有{status}的任务。"

    lines = []
    for r in rows:
        due = f"（截止 {r['due_date']}）" if r["due_date"] else ""
        lines.append(f"- [{r['task_id']}] {r['title']}{due} - {r['status']}")
    return f"共 {len(rows)} 条任务：\n" + "\n".join(lines)


@tool
def complete_task(task_id: int) -> str:
    """把指定任务标记为已完成。

    Args:
        task_id: 任务 ID，从 list_tasks 获取
    """
    conn = _conn()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET status = '已完成' WHERE task_id = ?", (task_id,))
    conn.commit()

    if cur.rowcount == 0:
        conn.close()
        return f"未找到任务 {task_id}。"

    conn.close()
    return f"✅ 任务 {task_id} 已标记为完成。"


ALL_TASK_TOOLS = [
    extract_tasks_from_email,
    list_tasks,
    complete_task,
]