# agent/email_tools.py
"""Agent Mail 邮件工具封装"""
import json
import subprocess
from langchain_core.tools import tool


def _run_cli(args: list) -> dict:
    """执行 agently-cli 命令，返回解析后的 JSON"""
    result = subprocess.run(
        ["agently-cli"] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=True,
    )

    output = result.stdout.strip()
    if not output:
        return {"ok": False, "error": result.stderr.strip() or "空输出"}

    # CLI 输出末尾可能有 "tip:" 行，只取第一个 { 到最后一个 } 之间的 JSON
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end == -1:
        return {"ok": False, "error": f"输出中找不到 JSON：{output[:200]}"}

    try:
        return json.loads(output[start:end + 1])
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"JSON 解析失败：{e}"}


def _format_message(m: dict) -> str:
    """把一封邮件的 dict 格式化成一行文本"""
    from_info = m.get("from", {})
    from_email = from_info.get("email", "未知") if isinstance(from_info, dict) else str(from_info)
    return (
        f"- ID: {m.get('message_id', '?')} | "
        f"来自: {from_email} | "
        f"主题: {m.get('subject', '(无主题)')} | "
        f"时间: {m.get('created_at', '?')}"
    )


@tool
def list_emails(limit: int = 10) -> str:
    """列出邮箱中最近的邮件。

    Args:
        limit: 返回的邮件数量，默认 10
    """
    data = _run_cli(["message", "+list", "--limit", str(limit)])
    if not data.get("ok"):
        return f"❌ 读取邮件失败：{data.get('error', data)}"

    messages = data.get("data", {}).get("data", [])
    if not messages:
        return "邮箱中没有邮件。"

    lines = [_format_message(m) for m in messages]
    return f"共 {len(messages)} 封邮件：\n" + "\n".join(lines)


@tool
def read_email(message_id: str) -> str:
    """读取指定邮件的完整内容（正文、发件人、时间）。

    Args:
        message_id: 邮件 ID，从 list_emails 或 search_emails 获取
    """
    data = _run_cli(["message", "+read", "--id", message_id])
    if not data.get("ok"):
        return f"❌ 读取邮件失败：{data.get('error', data)}"

    msg = data.get("data", {})
    from_info = msg.get("from", {})
    from_email = from_info.get("email", "未知") if isinstance(from_info, dict) else str(from_info)

    to_info = msg.get("to", [])
    to_str = ", ".join(
        t.get("email", "?") if isinstance(t, dict) else str(t)
        for t in to_info
    ) if isinstance(to_info, list) else str(to_info)

    return (
        f"发件人：{from_email}\n"
        f"收件人：{to_str}\n"
        f"主题：{msg.get('subject', '(无主题)')}\n"
        f"时间：{msg.get('created_at', '?')}\n"
        f"正文：\n{msg.get('body', msg.get('snippet', '（无正文）'))}"
    )


@tool
def search_emails(keyword: str, limit: int = 10) -> str:
    """按关键词搜索邮件（搜索主题和正文）。

    Args:
        keyword: 搜索关键词，例如 "会议"
        limit: 返回数量，默认 10
    """
    data = _run_cli(["message", "+search", "--q", keyword, "--limit", str(limit)])
    if not data.get("ok"):
        return f"❌ 搜索失败：{data.get('error', data)}"

    messages = data.get("data", {}).get("data", [])
    if not messages:
        return f"没有找到包含「{keyword}」的邮件。"

    lines = [_format_message(m) for m in messages]
    return f"找到 {len(messages)} 封邮件：\n" + "\n".join(lines)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件。会自动处理二次确认流程。

    Args:
        to: 收件人邮箱地址
        subject: 邮件主题
        body: 邮件正文
    """
    first = _run_cli([
        "message", "+send",
        "--to", to,
        "--subject", subject,
        "--body", body,
    ])

    if not first.get("ok"):
        return f"❌ 发送失败：{first.get('error', first)}"

    if not first.get("data", {}).get("confirmation_required"):
        return f"✅ 邮件已发送给 {to}"

    token = first["data"]["confirmation_token"]
    second = _run_cli([
        "message", "+send",
        "--to", to,
        "--subject", subject,
        "--body", body,
        "--confirmation-token", token,
    ])

    if not second.get("ok"):
        return f"❌ 确认发送失败：{second.get('error', second)}"

    return f"✅ 邮件已发送给 {to}，主题：{subject}"


ALL_EMAIL_TOOLS = [
    list_emails,
    read_email,
    search_emails,
    send_email,
]