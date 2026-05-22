from __future__ import annotations

from typing import Any, Dict

import requests

from settings import get_settings


def send_alert(token: str, title: str, body: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.firebase_server_key:
        return {"sent": False, "reason": "missing FIREBASE_SERVER_KEY"}

    response = requests.post(
        "https://fcm.googleapis.com/fcm/send",
        headers={
            "Authorization": f"key={settings.firebase_server_key}",
            "Content-Type": "application/json",
        },
        json={
            "to": token,
            "priority": "high",
            "notification": {"title": title, "body": body},
            "data": data or {},
        },
        timeout=settings.provider_timeout_seconds,
    )
    response.raise_for_status()
    return {"sent": True, "response": response.json()}
