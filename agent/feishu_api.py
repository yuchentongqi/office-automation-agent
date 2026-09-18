# agent/feishu_api.py
"""飞书 API 封装：日历日程 + 消息发送"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")

BASE_URL = "https://open.feishu.cn/open-apis"

# token 缓存（飞书的 token 有效期约 2 小时，缓存避免重复请求）
_token_cache = {"token": None, "expire_at": 0}


def get_tenant_access_token():
    """获取 tenant_access_token，带缓存"""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expire_at"]:
        return _token_cache["token"]

    url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": APP_ID,
        "app_secret": APP_SECRET,
    })
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败：{data}")

    token = data["tenant_access_token"]
    # 提前 5 分钟过期，避免边界情况
    expire_at = now + data.get("expire", 7200) - 300

    _token_cache["token"] = token
    _token_cache["expire_at"] = expire_at
    return token


def _headers():
    return {
        "Authorization": f"Bearer {get_tenant_access_token()}",
        "Content-Type": "application/json; charset=utf-8",
    }


def get_primary_calendar_id():
    """获取当前应用的主日历 ID"""
    url = f"{BASE_URL}/calendar/v4/calendars"
    resp = requests.get(url, headers=_headers())
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"获取日历列表失败：{data}")

    calendars = data.get("data", {}).get("calendar_list", [])
    for cal in calendars:
        if cal.get("type") == "primary":
            return cal["calendar_id"]

    # 没有 primary 就返回第一个
    if calendars:
        return calendars[0]["calendar_id"]
    raise RuntimeError("没有可用的日历")


def create_event(title: str, start_time: str, end_time: str, description: str = "") -> dict:
    """
    创建日历日程。

    Args:
        title: 日程标题
        start_time: 开始时间，格式 "2026-09-18 14:00:00"
        end_time: 结束时间，格式 "2026-09-18 15:00:00"
        description: 描述（可选）

    Returns:
        {"event_id": ..., "summary": ..., "start": ..., "end": ...}
    """
    calendar_id = get_primary_calendar_id()
    url = f"{BASE_URL}/calendar/v4/calendars/{calendar_id}/events"

    # 飞书用 Unix 时间戳（秒）
    def to_ts(s):
        return int(time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S")))

    body = {
        "summary": title,
        "description": description,
        "start_time": {
            "timestamp": str(to_ts(start_time)),
            "timezone": "Asia/Shanghai",
        },
        "end_time": {
            "timestamp": str(to_ts(end_time)),
            "timezone": "Asia/Shanghai",
        },
    }

    resp = requests.post(url, headers=_headers(), json=body)
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"创建日程失败：{data}")

    event = data["data"]["event"]
    return {
        "event_id": event.get("event_id"),
        "summary": event.get("summary"),
        "start": start_time,
        "end": end_time,
    }


def list_events(start_time: str, end_time: str) -> list:
    """
    查询某时间段的日程。

    Args:
        start_time: "2026-09-17 00:00:00"
        end_time: "2026-09-20 00:00:00"

    Returns:
        [{"summary": ..., "start": ..., "end": ...}, ...]
    """
    calendar_id = get_primary_calendar_id()
    url = f"{BASE_URL}/calendar/v4/calendars/{calendar_id}/events"

    def to_ts(s):
        return int(time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S")))

    params = {
        "start_time": str(to_ts(start_time)),
        "end_time": str(to_ts(end_time)),
    }

    resp = requests.get(url, headers=_headers(), params=params)
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"查询日程失败：{data}")

    events = []
    for item in data.get("data", {}).get("items", []):
        events.append({
            "summary": item.get("summary", "（无标题）"),
            "start": item.get("start_time", {}).get("timestamp"),
            "end": item.get("end_time", {}).get("timestamp"),
        })
    return events


def send_message(open_id: str, text: str) -> dict:
    """
    给指定用户发送飞书文本消息。

    Args:
        open_id: 用户的 open_id
        text: 消息内容
    """
    url = f"{BASE_URL}/im/v1/messages?receive_id_type=open_id"
    body = {
        "receive_id": open_id,
        "msg_type": "text",
        "content": f'{{"text": "{text}"}}',
    }
    resp = requests.post(url, headers=_headers(), json=body)
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"发送消息失败：{data}")

    return data.get("data", {})


if __name__ == "__main__":
    # 测试：获取 token + 列出日历
    print("正在测试飞书 API...")
    token = get_tenant_access_token()
    print(f"Token 获取成功：{token[:20]}...")

    calendar_id = get_primary_calendar_id()
    print(f"主日历 ID：{calendar_id}")