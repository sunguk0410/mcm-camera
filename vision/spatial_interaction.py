from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import monotonic

import cv2
import numpy as np
import requests

from backend_client import BackendClient
from config import (
    AR_DWELL_SECONDS,
    AR_SESSION_ID,
    AR_ZONE_RATIO,
    PERSON_EXIT_GRACE_SECONDS,
    ZONE_METADATA,
    ZONE_RATIOS,
)


@dataclass
class VisitState:
    customer_session_id: int
    last_seen_at: float
    current_zone: str | None = None
    zone_entered_at: datetime | None = None
    ar_entered_at: float | None = None
    ar_mapped: bool = False


class SpatialInteractionTracker:
    """Single-person demo state machine using the person's ground point."""

    def __init__(self, backend: BackendClient) -> None:
        self.backend = backend
        self.visit: VisitState | None = None

    def update(self, frame: np.ndarray, output_frame: np.ndarray, result) -> None:
        now = monotonic()
        observed_at = datetime.now().astimezone()
        point = self._find_person_ground_point(frame, result)

        if point is not None:
            if self.visit is None:
                self._start_visit(now)
            if self.visit is not None:
                self.visit.last_seen_at = now
                self._update_zone(frame, point, observed_at)
                self._update_ar(frame, point, now)
        elif self.visit is not None and now - self.visit.last_seen_at >= PERSON_EXIT_GRACE_SECONDS:
            self._finish_visit(observed_at)

        self._draw_layout(frame, output_frame, point, now)

    def close(self) -> None:
        if self.visit is not None:
            self._finish_visit(datetime.now().astimezone())

    def _start_visit(self, now: float) -> None:
        try:
            response = self.backend.create_customer_session()
            session_id = int(response["customerSessionId"])
            self.visit = VisitState(session_id, now)
            print(f"CustomerSession created: {session_id}")
        except (requests.RequestException, KeyError, TypeError, ValueError) as error:
            print(f"CustomerSession creation failed: {error}")

    def _finish_visit(self, exited_at: datetime) -> None:
        visit = self.visit
        if visit is None:
            return
        self._leave_zone(visit, exited_at)
        try:
            self.backend.end_customer_session(visit.customer_session_id)
            print(f"CustomerSession ended: {visit.customer_session_id}")
        except requests.RequestException as error:
            print(f"CustomerSession end failed: {error}")
        finally:
            self.visit = None

    def _update_zone(self, frame: np.ndarray, point: tuple[int, int], at: datetime) -> None:
        visit = self.visit
        if visit is None:
            return
        next_zone = next(
            (name for name, ratios in ZONE_RATIOS.items() if self._inside(point, self._box(frame, ratios))),
            None,
        )
        if next_zone == visit.current_zone:
            return
        self._leave_zone(visit, at)
        if next_zone is not None:
            visit.current_zone = next_zone
            visit.zone_entered_at = at
            print(f"Entered {next_zone}")

    def _leave_zone(self, visit: VisitState, exited_at: datetime) -> None:
        if visit.current_zone is None or visit.zone_entered_at is None:
            return
        zone = visit.current_zone
        floor_code, category_code = ZONE_METADATA[zone]
        try:
            self.backend.add_zone_interaction(
                visit.customer_session_id,
                floor_code,
                category_code,
                visit.zone_entered_at,
                exited_at,
            )
            print(f"ZoneInteraction sent: {zone}")
        except requests.RequestException as error:
            print(f"ZoneInteraction failed ({zone}): {error}")
        finally:
            visit.current_zone = None
            visit.zone_entered_at = None

    def _update_ar(self, frame: np.ndarray, point: tuple[int, int], now: float) -> None:
        visit = self.visit
        if visit is None or visit.ar_mapped:
            return
        if not self._inside(point, self._box(frame, AR_ZONE_RATIO)):
            visit.ar_entered_at = None
            return
        if visit.ar_entered_at is None:
            visit.ar_entered_at = now
            return
        if now - visit.ar_entered_at < AR_DWELL_SECONDS or AR_SESSION_ID is None:
            return
        try:
            self.backend.map_ar_session(AR_SESSION_ID, visit.customer_session_id)
            visit.ar_mapped = True
            print(f"ARSession {AR_SESSION_ID} mapped to CustomerSession {visit.customer_session_id}")
        except requests.RequestException as error:
            print(f"ARSession mapping failed: {error}")

    @staticmethod
    def _find_person_ground_point(frame: np.ndarray, result) -> tuple[int, int] | None:
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return None
        height, width = frame.shape[:2]
        candidates = []
        for x1, y1, x2, y2 in boxes.xyxy.cpu().tolist():
            area = max(0.0, (x2 - x1) * (y2 - y1))
            if area >= width * height * 0.02:
                candidates.append((area, (int((x1 + x2) / 2), int(y2))))
        return max(candidates, default=(0, None), key=lambda item: item[0])[1]

    def _draw_layout(self, frame: np.ndarray, output: np.ndarray, point, now: float) -> None:
        active = self.visit.current_zone if self.visit else None
        for name, ratios in ZONE_RATIOS.items():
            x1, y1, x2, y2 = self._box(frame, ratios)
            color = (0, 255, 0) if name == active else (255, 180, 0)
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            floor, category = ZONE_METADATA[name]
            cv2.putText(output, f"{name} {floor}/{category}", (x1 + 5, y1 + 22), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
        x1, y1, x2, y2 = self._box(frame, AR_ZONE_RATIO)
        cv2.rectangle(output, (x1, y1), (x2, y2), (255, 0, 255), 2)
        label = "AR FITTING"
        if self.visit and self.visit.ar_mapped:
            label += " [MAPPED]"
        elif self.visit and self.visit.ar_entered_at is not None:
            label += f" [{min(AR_DWELL_SECONDS, now - self.visit.ar_entered_at):.1f}/{AR_DWELL_SECONDS:.0f}s]"
        elif AR_SESSION_ID is None:
            label += " [SET MCM_AR_SESSION_ID]"
        cv2.putText(output, label, (x1 + 5, y1 + 22), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 0, 255), 2)
        if point is not None:
            cv2.circle(output, point, 8, (0, 0, 255), -1)

    @staticmethod
    def _box(frame: np.ndarray, ratios) -> tuple[int, int, int, int]:
        height, width = frame.shape[:2]
        left, top, right, bottom = ratios
        return int(width * left), int(height * top), int(width * right), int(height * bottom)

    @staticmethod
    def _inside(point: tuple[int, int], box: tuple[int, int, int, int]) -> bool:
        x, y = point
        x1, y1, x2, y2 = box
        return x1 <= x <= x2 and y1 <= y <= y2
