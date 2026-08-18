from __future__ import annotations

from datetime import datetime
from typing import Any

import requests


class BackendClient:
    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def create_customer_session(self) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/customer-sessions",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def end_customer_session(self, customer_session_id: int) -> None:
        response = requests.patch(
            f"{self.base_url}/api/customer-sessions/{customer_session_id}/end",
            timeout=self.timeout,
        )
        response.raise_for_status()

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

    def map_ar_session(
        self,
        ar_session_id: int,
        customer_session_id: int,
    ) -> None:
        response = requests.patch(
            f"{self.base_url}/api/ar-sessions/{ar_session_id}/customer-session",
            json={"customerSessionId": customer_session_id},
            timeout=self.timeout,
        )
        response.raise_for_status()

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        # Spring DTO uses LocalDateTime, so no UTC suffix/offset is sent.
        return value.astimezone().replace(tzinfo=None).isoformat(timespec="milliseconds")
