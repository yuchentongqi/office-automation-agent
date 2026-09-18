# agent/tools.py
"""Agent 可调用的工具：飞书日历 + 消息"""
from datetime import datetime, timedelta

from langchain_core.tools import tool

from agent.feishu_api import (
    create_event,
    list_events,
    send_message,
)


@tool
def create_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    description: str = "",
) -> str:
    """创建一个飞书日历日程。

    Args:
        title: 日程标题，例如 "产品评审会"
        start_time: 开始时间，格式必须为 "YYYY-MM-DD HH:MM:SS"，例如 "2026-09-18 14:00:00"
        end_time: 结束时间，格式必须为 "YYYY-MM-DD HH:MM:SS"，例如 "2026-09-18 15:00:00"
        description: 日程描述，可选
    """
    try:
        result = create_event(title, start_time, end_time, description)
        return (
            f"✅ 日程创建成功\n"
            f"标题：{result['summary']}\n"
            f"时间：{result['start']} ~ {result['end']}\n"
            f"事件 ID：{result['event_id']}"
        )
    except Exception as e:
        return f"❌ 创建日程失败：{e}"


@tool
def list_calendar_events(start_time: str, end_time: str) -> str:
    """查询某个时间段内的飞书日历日程。

    Args:
        start_time: 查询起始时间，格式 "YYYY-MM-DD HH:MM:SS"
        end_time: 查询结束时间，格式 "YYYY-MM-DD HH:MM:SS"
    """
    try:
        events = list_events(start_time, end_time)
        if not events:
            return f"{start_time} 到 {end_time} 之间没有日程。"

        lines = []
        for i, ev in enumerate(events, 1):
            lines.append(f"{i}. {ev['summary']}（{ev['start']} ~ {ev['end']}）")
        return f"共 {len(events)} 个日程：\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ 查询日程失败：{e}"


@tool
def send_feishu_message(open_id: str, text: str) -> str:
    """给指定飞书用户发送文本消息。

    Args:
        open_id: 接收者的 open_id（用户唯一标识）
        text: 消息内容
    """
    try:
        send_message(open_id, text)
        return f"✅ 消息已发送给 {open_id}"
    except Exception as e:
        return f"❌ 发送消息失败：{e}"


@tool
def get_current_time() -> str:
    """获取当前日期和时间。在需要计算"明天"、"下周"等相对时间时，先调用这个工具获取当前时间。"""
    now = datetime.now()
    weekday = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
    return (
        f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}（星期{weekday}）\n"
        f"今天：{now.strftime('%Y-%m-%d')}\n"
        f"明天：{(now + timedelta(days=1)).strftime('%Y-%m-%d')}"
    )


ALL_TOOLS = [
    create_calendar_event,
    list_calendar_events,
    send_feishu_message,
    get_current_time,
]