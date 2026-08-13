from __future__ import annotations

from datetime import datetime
from typing import Any

import requests


class BackendClient:
    def __init__(
        self,
        base_url: str = "https://api.mcm-showcase.com",
        timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def create_or_get_session(
        self,
        camera_id: str,
        track_id: int,
    ) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/customer-sessions",
            json={
                "cameraId": camera_id,
                "trackId": track_id,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()

    def add_zone_interaction(
        self,
        customer_session_id: int,
        floor_code: str,
        category_code: str,
        entered_at: datetime,
        exited_at: datetime,
    ) -> None:
        response = requests.post(
            f"{self.base_url}/api/zone-interactions",
            json={
                "customerSessionId": customer_session_id,
                "floorCode": floor_code,
                "categoryCode": category_code,
                "enteredAt": self._format_datetime(entered_at),
                "exitedAt": self._format_datetime(exited_at),
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        return value.isoformat(timespec="milliseconds").replace(
            "+00:00",
            "Z",
        )
