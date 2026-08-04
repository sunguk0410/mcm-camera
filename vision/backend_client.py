from __future__ import annotations

from typing import Any

import requests


class BackendClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
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

    def add_interaction(
        self,
        customer_session_id: int,
        product_id: str,
        interaction_type: str = "PICKED_UP",
    ) -> None:
        response = requests.post(
            (
                f"{self.base_url}"
                f"/api/customer-sessions/"
                f"{customer_session_id}"
                f"/interactions"
            ),
            json={
                "productId": product_id,
                "interactionType": (
                    interaction_type
                ),
            },
            timeout=self.timeout,
        )

        response.raise_for_status()