# customer_tracker.py

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

import cv2
import numpy as np
import requests

from backend_client import BackendClient
from config import (
    APPEARANCE_MATCH_THRESHOLD,
    CAMERA_ID,
    MIN_PERSON_AREA_RATIO,
    SESSION_TTL_SECONDS,
)


@dataclass
class CustomerMemory:
    session_id: int
    last_seen_at: float
    appearance: np.ndarray


@dataclass
class TrackingOutput:
    track_to_customer: dict[int, CustomerMemory]
    track_wrists: dict[int, list[tuple[int, int]]]


class CustomerTracker:
    def __init__(
        self,
        backend: BackendClient,
    ) -> None:
        self.backend = backend

        # YOLO Track ID → 실제 고객 세션
        self.track_to_customer: dict[
            int,
            CustomerMemory,
        ] = {}

        # 최근 5분 동안 기억 중인 고객
        self.customer_memories: list[
            CustomerMemory
        ] = []

    def update(
        self,
        frame: np.ndarray,
        result,
    ) -> TrackingOutput:
        now = monotonic()

        track_wrists: dict[
            int,
            list[tuple[int, int]],
        ] = {}

        boxes = result.boxes

        if (
            boxes is None
            or boxes.id is None
            or len(boxes) == 0
        ):
            self._remove_expired_customers(now)

            return TrackingOutput(
                track_to_customer=self.track_to_customer,
                track_wrists=track_wrists,
            )

        track_ids = (
            boxes.id
            .int()
            .cpu()
            .tolist()
        )

        coordinates = (
            boxes.xyxy
            .cpu()
            .tolist()
        )

        keypoints_xy = None
        keypoints_confidence = None

        if (
            result.keypoints is not None
            and result.keypoints.xy is not None
        ):
            keypoints_xy = (
                result.keypoints.xy
                .cpu()
                .numpy()
            )

            if result.keypoints.conf is not None:
                keypoints_confidence = (
                    result.keypoints.conf
                    .cpu()
                    .numpy()
                )

        for index, (track_id, person_box) in enumerate(
            zip(track_ids, coordinates)
        ):
            if self._is_too_small_person(
                frame,
                person_box,
            ):
                continue

            appearance = self._extract_appearance(
                frame,
                person_box,
            )

            customer = self.track_to_customer.get(
                track_id
            )

            # 새로운 Track ID가 생긴 경우
            if customer is None and appearance is not None:
                customer = self._find_recent_customer(
                    appearance=appearance,
                    now=now,
                )

                if customer is not None:
                    self.track_to_customer[
                        track_id
                    ] = customer

                    score = self._appearance_similarity(
                        appearance,
                        customer.appearance,
                    )

                    print(
                        "기존 고객 복구: "
                        f"Track {track_id} → "
                        f"Session {customer.session_id} "
                        f"(유사도 {score:.2f})"
                    )

                else:
                    customer = self._create_customer(
                        track_id=track_id,
                        appearance=appearance,
                        now=now,
                    )

            if customer is None:
                continue

            customer.last_seen_at = now

            if appearance is not None:
                customer.appearance = (
                    customer.appearance * 0.95
                    + appearance * 0.05
                ).astype(np.float32)

            if (
                keypoints_xy is not None
                and index < len(keypoints_xy)
            ):
                confidence = None

                if (
                    keypoints_confidence is not None
                    and index
                    < len(keypoints_confidence)
                ):
                    confidence = (
                        keypoints_confidence[index]
                    )

                track_wrists[track_id] = (
                    self._extract_wrists(
                        keypoints=keypoints_xy[index],
                        confidence=confidence,
                    )
                )

        self._remove_expired_customers(now)

        return TrackingOutput(
            track_to_customer=self.track_to_customer,
            track_wrists=track_wrists,
        )

    def draw_customer_labels(
        self,
        frame: np.ndarray,
        result,
    ) -> None:
        boxes = result.boxes

        if (
            boxes is None
            or boxes.id is None
            or len(boxes) == 0
        ):
            return

        track_ids = (
            boxes.id
            .int()
            .cpu()
            .tolist()
        )

        coordinates = (
            boxes.xyxy
            .cpu()
            .tolist()
        )

        for track_id, person_box in zip(
            track_ids,
            coordinates,
        ):
            customer = self.track_to_customer.get(
                track_id
            )

            if customer is None:
                continue

            x1, y1, x2, y2 = map(
                int,
                person_box,
            )

            cv2.putText(
                frame,
                (
                    f"Track {track_id} / "
                    f"Session {customer.session_id}"
                ),
                (x1, max(30, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
            )

    @staticmethod
    def draw_wrists(
        frame: np.ndarray,
        track_wrists: dict[
            int,
            list[tuple[int, int]],
        ],
    ) -> None:
        for wrists in track_wrists.values():
            for wrist in wrists:
                cv2.circle(
                    frame,
                    wrist,
                    7,
                    (255, 255, 255),
                    -1,
                )

    def _create_customer(
        self,
        track_id: int,
        appearance: np.ndarray,
        now: float,
    ) -> CustomerMemory | None:
        try:
            response = (
                self.backend.create_or_get_session(
                    camera_id=CAMERA_ID,
                    track_id=track_id,
                )
            )

            session_id = self._get_session_id(
                response
            )

            customer = CustomerMemory(
                session_id=session_id,
                last_seen_at=now,
                appearance=appearance.copy(),
            )

            self.customer_memories.append(
                customer
            )

            self.track_to_customer[
                track_id
            ] = customer

            print(
                "새 고객 생성: "
                f"Track {track_id} → "
                f"Session {session_id}"
            )

            return customer

        except (
            requests.RequestException,
            KeyError,
            ValueError,
        ) as error:
            print(
                "고객 세션 생성 실패:",
                error,
            )

            return None

    def _find_recent_customer(
        self,
        appearance: np.ndarray,
        now: float,
    ) -> CustomerMemory | None:
        """
        새로운 Track ID가 나타나도 최근 5분 동안
        외형이 비슷한 고객이 있으면 기존 세션을 재사용한다.

        active session을 제외하지 않는다.
        같은 사람이 Track 1과 Track 2로 잠깐 중복 감지되는 경우에도
        새로운 세션이 생성되는 것을 막기 위함이다.
        """
        best_customer = None
        best_score = (
            APPEARANCE_MATCH_THRESHOLD
        )

        for memory in self.customer_memories:
            elapsed = (
                now - memory.last_seen_at
            )

            if elapsed > SESSION_TTL_SECONDS:
                continue

            score = self._appearance_similarity(
                appearance,
                memory.appearance,
            )

            if score > best_score:
                best_score = score
                best_customer = memory

        return best_customer

    @staticmethod
    def _extract_appearance(
        frame: np.ndarray,
        person_box: list[float],
    ) -> np.ndarray | None:
        frame_height, frame_width = (
            frame.shape[:2]
        )

        x1, y1, x2, y2 = map(
            int,
            person_box,
        )

        x1 = max(
            0,
            min(x1, frame_width - 1),
        )
        x2 = max(
            0,
            min(x2, frame_width),
        )
        y1 = max(
            0,
            min(y1, frame_height - 1),
        )
        y2 = max(
            0,
            min(y2, frame_height),
        )

        if x2 <= x1 or y2 <= y1:
            return None

        person = frame[
            y1:y2,
            x1:x2,
        ]

        if person.size == 0:
            return None

        person_height, person_width = (
            person.shape[:2]
        )

        # 얼굴과 다리를 제외한 몸통 중앙
        torso_y1 = int(
            person_height * 0.20
        )
        torso_y2 = int(
            person_height * 0.65
        )
        torso_x1 = int(
            person_width * 0.15
        )
        torso_x2 = int(
            person_width * 0.85
        )

        torso = person[
            torso_y1:torso_y2,
            torso_x1:torso_x2,
        ]

        if torso.size == 0:
            return None

        hsv = cv2.cvtColor(
            torso,
            cv2.COLOR_BGR2HSV,
        )

        histogram = cv2.calcHist(
            [hsv],
            [0, 1],
            None,
            [30, 32],
            [0, 180, 0, 256],
        )

        cv2.normalize(
            histogram,
            histogram,
            alpha=0,
            beta=1,
            norm_type=cv2.NORM_MINMAX,
        )

        return (
            histogram
            .flatten()
            .astype(np.float32)
        )

    @staticmethod
    def _appearance_similarity(
        first: np.ndarray,
        second: np.ndarray,
    ) -> float:
        return float(
            cv2.compareHist(
                first,
                second,
                cv2.HISTCMP_CORREL,
            )
        )

    @staticmethod
    def _extract_wrists(
        keypoints: np.ndarray,
        confidence: np.ndarray | None,
    ) -> list[tuple[int, int]]:
        """
        COCO Pose 기준:
        9  = 왼쪽 손목
        10 = 오른쪽 손목
        """
        wrists: list[
            tuple[int, int]
        ] = []

        for wrist_index in (9, 10):
            if wrist_index >= len(keypoints):
                continue

            x, y = keypoints[wrist_index]

            if x <= 0 or y <= 0:
                continue

            if (
                confidence is not None
                and wrist_index < len(confidence)
                and confidence[wrist_index]
                < 0.35
            ):
                continue

            wrists.append(
                (int(x), int(y))
            )

        return wrists

    @staticmethod
    def _is_too_small_person(
        frame: np.ndarray,
        person_box: list[float],
    ) -> bool:
        frame_height, frame_width = (
            frame.shape[:2]
        )

        frame_area = (
            frame_height * frame_width
        )

        x1, y1, x2, y2 = person_box

        person_area = max(
            0,
            (x2 - x1) * (y2 - y1),
        )

        return (
            person_area
            < frame_area
            * MIN_PERSON_AREA_RATIO
        )

    def _remove_expired_customers(
        self,
        now: float,
    ) -> None:
        self.customer_memories[:] = [
            memory
            for memory in self.customer_memories
            if (
                now - memory.last_seen_at
                <= SESSION_TTL_SECONDS
            )
        ]

        valid_session_ids = {
            memory.session_id
            for memory
            in self.customer_memories
        }

        self.track_to_customer = {
            track_id: customer
            for track_id, customer
            in self.track_to_customer.items()
            if customer.session_id
            in valid_session_ids
        }

    @staticmethod
    def _get_session_id(
        response: dict,
    ) -> int:
        possible_keys = (
            "customerSessionId",
            "sessionId",
            "id",
        )

        for key in possible_keys:
            value = response.get(key)

            if value is not None:
                return int(value)

        raise KeyError(
            "고객 세션 ID를 찾을 수 없습니다. "
            f"응답: {response}"
        )