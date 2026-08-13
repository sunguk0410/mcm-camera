# pickup_detector.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import monotonic

import cv2
import numpy as np
import requests

from backend_client import BackendClient
from config import (
    CALIBRATION_DELAY_SECONDS,
    FLOOR_CODE,
    PICKUP_CONFIRM_SECONDS,
    PICKUP_COOLDOWN_SECONDS,
    PRODUCT_ZONE_RATIOS,
    ZONE_CHANGE_THRESHOLD,
    ZONE_RESTORE_SECONDS,
    ZONE_RESTORE_THRESHOLD,
)
from customer_tracker import CustomerMemory


@dataclass
class ProductZoneState:
    baseline: np.ndarray | None = None

    change_started_at: float | None = None
    restored_started_at: float | None = None

    candidate_session_id: int | None = None

    last_pickup_at: float = 0.0
    picked_up: bool = False


class PickupDetector:
    def __init__(
        self,
        backend: BackendClient,
    ) -> None:
        self.backend = backend

        self.states = {
            product_id: ProductZoneState()
            for product_id
            in PRODUCT_ZONE_RATIOS
        }

        self.started_at = monotonic()
        self.calibration_completed = False

    def update(
        self,
        frame: np.ndarray,
        output_frame: np.ndarray,
        track_to_customer: dict[
            int,
            CustomerMemory,
        ],
        track_wrists: dict[
            int,
            list[tuple[int, int]],
        ],
    ) -> None:
        now = monotonic()

        product_zones = {
            product_id: self._ratio_to_box(
                frame,
                ratios,
            )
            for product_id, ratios
            in PRODUCT_ZONE_RATIOS.items()
        }

        if (
            not self.calibration_completed
            and now - self.started_at
            >= CALIBRATION_DELAY_SECONDS
        ):
            self.calibrate(
                frame,
                product_zones,
            )

        for product_id, zone in (
            product_zones.items()
        ):
            state = self.states[
                product_id
            ]

            zone_image = (
                self._extract_zone_image(
                    frame,
                    zone,
                )
            )

            change_score = None

            if (
                state.baseline is not None
                and zone_image is not None
            ):
                change_score = (
                    self._calculate_change(
                        state.baseline,
                        zone_image,
                    )
                )

            touching_sessions = (
                self._find_touching_sessions(
                    zone=zone,
                    track_to_customer=(
                        track_to_customer
                    ),
                    track_wrists=track_wrists,
                )
            )

            self._process_product_state(
                product_id=product_id,
                state=state,
                touching_sessions=(
                    touching_sessions
                ),
                change_score=change_score,
                now=now,
            )

            self._draw_zone(
                frame=output_frame,
                product_id=product_id,
                zone=zone,
                state=state,
                change_score=change_score,
            )

        self._draw_instruction(
            output_frame,
            now,
        )

    def calibrate(
        self,
        frame: np.ndarray,
        product_zones: dict[
            str,
            tuple[int, int, int, int],
        ] | None = None,
    ) -> None:
        if product_zones is None:
            product_zones = {
                product_id: (
                    self._ratio_to_box(
                        frame,
                        ratios,
                    )
                )
                for product_id, ratios
                in PRODUCT_ZONE_RATIOS.items()
            }

        for product_id, zone in (
            product_zones.items()
        ):
            image = (
                self._extract_zone_image(
                    frame,
                    zone,
                )
            )

            if image is None:
                continue

            state = self.states[
                product_id
            ]

            state.baseline = image.copy()
            state.change_started_at = None
            state.restored_started_at = None
            state.candidate_session_id = None
            state.picked_up = False

        self.calibration_completed = True

        print(
            "제품 진열 구역 기준 화면 "
            "저장 완료"
        )

    def _process_product_state(
        self,
        product_id: str,
        state: ProductZoneState,
        touching_sessions: list[int],
        change_score: float | None,
        now: float,
    ) -> None:
        if state.baseline is None:
            return

        if not state.picked_up:
            self._process_ready_product(
                product_id=product_id,
                state=state,
                touching_sessions=(
                    touching_sessions
                ),
                change_score=change_score,
                now=now,
            )

        else:
            self._process_picked_product(
                product_id=product_id,
                state=state,
                change_score=change_score,
                now=now,
            )

    def _process_ready_product(
        self,
        product_id: str,
        state: ProductZoneState,
        touching_sessions: list[int],
        change_score: float | None,
        now: float,
    ) -> None:
        has_hand_near_product = bool(
            touching_sessions
        )

        has_product_moved = (
            change_score is not None
            and change_score
            >= ZONE_CHANGE_THRESHOLD
        )

        if (
            not has_hand_near_product
            or not has_product_moved
        ):
            state.change_started_at = None
            state.candidate_session_id = None
            return

        if state.change_started_at is None:
            state.change_started_at = now
            state.candidate_session_id = (
                touching_sessions[0]
            )

            return

        changed_duration = (
            now - state.change_started_at
        )

        cooldown_finished = (
            now - state.last_pickup_at
            >= PICKUP_COOLDOWN_SECONDS
        )

        if (
            changed_duration
            < PICKUP_CONFIRM_SECONDS
            or not cooldown_finished
            or state.candidate_session_id
            is None
        ):
            return

        try:
            exited_at = datetime.now(timezone.utc)
            entered_at = exited_at - timedelta(
                seconds=changed_duration
            )

            self.backend.add_zone_interaction(
                customer_session_id=(
                    state.candidate_session_id
                ),
                floor_code=FLOOR_CODE,
                category_code=product_id,
                entered_at=entered_at,
                exited_at=exited_at,
            )

            state.picked_up = True
            state.last_pickup_at = now
            state.change_started_at = None

            print(
                "실제 집기 감지: "
                f"Session "
                f"{state.candidate_session_id} "
                f"→ {product_id}"
            )

        except requests.RequestException as error:
            print(
                "제품 상호작용 저장 실패:",
                error,
            )

            state.change_started_at = None
            state.candidate_session_id = None

    @staticmethod
    def _process_picked_product(
        product_id: str,
        state: ProductZoneState,
        change_score: float | None,
        now: float,
    ) -> None:
        product_restored = (
            change_score is not None
            and change_score
            <= ZONE_RESTORE_THRESHOLD
        )

        if not product_restored:
            state.restored_started_at = None
            return

        if state.restored_started_at is None:
            state.restored_started_at = now
            return

        restored_duration = (
            now - state.restored_started_at
        )

        if (
            restored_duration
            < ZONE_RESTORE_SECONDS
        ):
            return

        state.picked_up = False
        state.restored_started_at = None
        state.candidate_session_id = None

        print(
            f"{product_id}가 원래 위치로 "
            "돌아와 다시 감지 가능"
        )

    @staticmethod
    def _find_touching_sessions(
        zone: tuple[int, int, int, int],
        track_to_customer: dict[
            int,
            CustomerMemory,
        ],
        track_wrists: dict[
            int,
            list[tuple[int, int]],
        ],
    ) -> list[int]:
        touching_sessions: list[int] = []

        for track_id, wrists in (
            track_wrists.items()
        ):
            customer = (
                track_to_customer.get(
                    track_id
                )
            )

            if customer is None:
                continue

            wrist_is_near = any(
                PickupDetector._point_inside_box(
                    point=wrist,
                    box=zone,
                    margin=35,
                )
                for wrist in wrists
            )

            if wrist_is_near:
                touching_sessions.append(
                    customer.session_id
                )

        return touching_sessions

    @staticmethod
    def _ratio_to_box(
        frame: np.ndarray,
        ratios: tuple[
            float,
            float,
            float,
            float,
        ],
    ) -> tuple[int, int, int, int]:
        height, width = frame.shape[:2]

        left, top, right, bottom = (
            ratios
        )

        return (
            int(width * left),
            int(height * top),
            int(width * right),
            int(height * bottom),
        )

    @staticmethod
    def _extract_zone_image(
        frame: np.ndarray,
        zone: tuple[int, int, int, int],
    ) -> np.ndarray | None:
        frame_height, frame_width = (
            frame.shape[:2]
        )

        x1, y1, x2, y2 = zone

        x1 = max(
            0,
            min(x1, frame_width - 1),
        )
        y1 = max(
            0,
            min(y1, frame_height - 1),
        )
        x2 = max(
            x1 + 1,
            min(x2, frame_width),
        )
        y2 = max(
            y1 + 1,
            min(y2, frame_height),
        )

        roi = frame[
            y1:y2,
            x1:x2,
        ]

        if roi.size == 0:
            return None

        gray = cv2.cvtColor(
            roi,
            cv2.COLOR_BGR2GRAY,
        )

        resized = cv2.resize(
            gray,
            (160, 120),
            interpolation=cv2.INTER_AREA,
        )

        return cv2.GaussianBlur(
            resized,
            (5, 5),
            0,
        )

    @staticmethod
    def _calculate_change(
        baseline: np.ndarray,
        current: np.ndarray,
    ) -> float:
        difference = cv2.absdiff(
            baseline,
            current,
        )

        return float(
            np.mean(difference)
        )

    @staticmethod
    def _point_inside_box(
        point: tuple[int, int],
        box: tuple[int, int, int, int],
        margin: int = 0,
    ) -> bool:
        x, y = point
        x1, y1, x2, y2 = box

        return (
            x1 - margin <= x
            <= x2 + margin
            and y1 - margin <= y
            <= y2 + margin
        )

    @staticmethod
    def _draw_zone(
        frame: np.ndarray,
        product_id: str,
        zone: tuple[int, int, int, int],
        state: ProductZoneState,
        change_score: float | None,
    ) -> None:
        x1, y1, x2, y2 = zone

        if state.picked_up:
            status = "PICKED"

        elif state.baseline is None:
            status = "CALIBRATING"

        elif state.change_started_at is not None:
            status = "CHANGED"

        else:
            status = "READY"

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (255, 255, 255),
            2,
        )

        label = (
            f"{product_id} [{status}]"
        )

        if change_score is not None:
            label += (
                f" diff={change_score:.1f}"
            )

        cv2.putText(
            frame,
            label,
            (x1, max(25, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
        )

    def _draw_instruction(
        self,
        frame: np.ndarray,
        now: float,
    ) -> None:
        if not self.calibration_completed:
            remaining = max(
                0.0,
                CALIBRATION_DELAY_SECONDS
                - (now - self.started_at),
            )

            text = (
                "Keep bags still - "
                f"calibrating {remaining:.1f}s"
            )

        else:
            text = (
                "C: Recalibrate | Q: Quit"
            )

        cv2.putText(
            frame,
            text,
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.70,
            (255, 255, 255),
            2,
        )
