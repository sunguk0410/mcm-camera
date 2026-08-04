from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import TypeAlias

import cv2
import numpy as np
import requests
from ultralytics import YOLO

from backend_client import BackendClient


# ============================================================
# 기본 설정
# ============================================================

CAMERA_ID = "CAMERA_01"
CAMERA_INDEX = 0

# YOLO Pose 모델
MODEL_NAME = "yolo26n-pose.pt"

# 사람이 사라진 후 기존 고객으로 기억할 시간
SESSION_TTL_SECONDS = 5 * 60

# 옷 색상 유사도 기준
# 높일수록 더 비슷해야 같은 사람으로 판단
APPEARANCE_MATCH_THRESHOLD = 0.65

# 제품 구역이 기준 화면과 얼마나 달라져야
# 가방이 이동했다고 판단할지
ZONE_CHANGE_THRESHOLD = 22.0

# 변화가 이 시간 이상 유지돼야 집기로 판단
PICKUP_CONFIRM_SECONDS = 0.8

# 같은 고객·제품이 중복 저장되지 않도록 하는 시간
PICKUP_COOLDOWN_SECONDS = 10.0

# 진열 구역이 원래 상태로 복구됐다고 판단하는 기준
ZONE_RESTORE_THRESHOLD = 12.0

# 복구 상태가 유지돼야 제품을 다시 감지할 수 있음
ZONE_RESTORE_SECONDS = 1.0

# 프로그램 시작 후 진열대 기준 화면을 저장하기까지 대기 시간
CALIBRATION_DELAY_SECONDS = 3.0


Box: TypeAlias = tuple[int, int, int, int]
Point: TypeAlias = tuple[int, int]


# ============================================================
# 제품 진열 구역
# ============================================================
#
# 값은 화면 전체 크기에 대한 비율이다.
#
# (왼쪽 비율, 위쪽 비율, 오른쪽 비율, 아래쪽 비율)
#
# 현재 예시는:
# BAG_A = 화면 왼쪽
# BAG_B = 화면 오른쪽
#
# 실제 카메라 화면에서 가방이 놓인 위치에 맞게 수정해야 한다.
# ============================================================

PRODUCT_ZONE_RATIOS: dict[
    str,
    tuple[float, float, float, float],
] = {
    "BAG_A": (0.03, 0.25, 0.35, 0.90),
    "BAG_B": (0.65, 0.25, 0.97, 0.90),
}


# ============================================================
# 데이터 클래스
# ============================================================

@dataclass
class CustomerMemory:
    session_id: int
    last_seen_at: float
    appearance: np.ndarray


@dataclass
class ProductZoneState:
    baseline: np.ndarray | None = None
    change_started_at: float | None = None
    restored_started_at: float | None = None
    last_pickup_at: float = 0.0
    picked_up: bool = False
    candidate_session_id: int | None = None


# ============================================================
# 공통 함수
# ============================================================

def get_session_id(response: dict) -> int:
    """
    백엔드 응답에서 고객 세션 ID를 꺼낸다.

    백엔드 DTO에 따라 다음 중 하나일 수 있으므로
    여러 필드 이름을 지원한다.
    """
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
        "고객 세션 ID를 응답에서 찾을 수 없습니다. "
        f"응답 내용: {response}"
    )


def ratio_to_box(
    frame: np.ndarray,
    ratios: tuple[float, float, float, float],
) -> Box:
    height, width = frame.shape[:2]

    left, top, right, bottom = ratios

    return (
        int(width * left),
        int(height * top),
        int(width * right),
        int(height * bottom),
    )


def clamp_box(
    frame: np.ndarray,
    box: Box,
) -> Box:
    height, width = frame.shape[:2]

    x1, y1, x2, y2 = box

    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(x1 + 1, min(x2, width))
    y2 = max(y1 + 1, min(y2, height))

    return x1, y1, x2, y2


def box_center(box: list[float] | tuple[float, ...]) -> Point:
    x1, y1, x2, y2 = box

    return (
        int((x1 + x2) / 2),
        int((y1 + y2) / 2),
    )


def point_inside_box(
    point: Point,
    box: Box,
    margin: int = 0,
) -> bool:
    x, y = point
    x1, y1, x2, y2 = box

    return (
        x1 - margin <= x <= x2 + margin
        and y1 - margin <= y <= y2 + margin
    )


# ============================================================
# 고객 재인식
# ============================================================

def extract_appearance(
    frame: np.ndarray,
    person_box: list[float],
) -> np.ndarray | None:
    """
    사람 박스의 몸통 부분에서 HSV 색상 히스토그램을 추출한다.

    얼굴 자체를 저장하는 방식이 아니라
    옷 색상 특징을 이용하는 간단한 MVP 방식이다.
    """
    height, width = frame.shape[:2]

    x1, y1, x2, y2 = map(int, person_box)

    x1 = max(0, min(x1, width - 1))
    x2 = max(0, min(x2, width))
    y1 = max(0, min(y1, height - 1))
    y2 = max(0, min(y2, height))

    if x2 <= x1 or y2 <= y1:
        return None

    person = frame[y1:y2, x1:x2]

    if person.size == 0:
        return None

    person_height = person.shape[0]
    person_width = person.shape[1]

    # 얼굴과 다리를 제외하고 몸통 중심부만 사용
    torso_y1 = int(person_height * 0.20)
    torso_y2 = int(person_height * 0.65)

    torso_x1 = int(person_width * 0.15)
    torso_x2 = int(person_width * 0.85)

    torso = person[
        torso_y1:torso_y2,
        torso_x1:torso_x2,
    ]

    if torso.size == 0:
        return None

    hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)

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

    return histogram.flatten().astype(np.float32)


def appearance_similarity(
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


def find_recent_customer(
    appearance: np.ndarray,
    memories: list[CustomerMemory],
    active_session_ids: set[int],
    now: float,
) -> tuple[CustomerMemory | None, float]:
    best_memory: CustomerMemory | None = None
    best_score = APPEARANCE_MATCH_THRESHOLD

    for memory in memories:
        elapsed = now - memory.last_seen_at

        if elapsed > SESSION_TTL_SECONDS:
            continue

        # 현재 화면에 이미 등장해 있는 고객과
        # 새 Track ID가 중복 매칭되는 것을 막는다.
        if memory.session_id in active_session_ids:
            continue

        score = appearance_similarity(
            appearance,
            memory.appearance,
        )

        if score > best_score:
            best_score = score
            best_memory = memory

    return best_memory, best_score


# ============================================================
# 제품 진열 구역 변화 감지
# ============================================================

def extract_zone_image(
    frame: np.ndarray,
    zone: Box,
) -> np.ndarray | None:
    x1, y1, x2, y2 = clamp_box(frame, zone)

    roi = frame[y1:y2, x1:x2]

    if roi.size == 0:
        return None

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # 카메라 해상도와 관계없이 동일한 크기로 비교
    resized = cv2.resize(
        gray,
        (160, 120),
        interpolation=cv2.INTER_AREA,
    )

    # 약간의 노이즈 제거
    blurred = cv2.GaussianBlur(
        resized,
        (5, 5),
        0,
    )

    return blurred


def calculate_zone_change(
    baseline: np.ndarray,
    current: np.ndarray,
) -> float:
    difference = cv2.absdiff(
        baseline,
        current,
    )

    return float(np.mean(difference))


def calibrate_product_zones(
    frame: np.ndarray,
    zones: dict[str, Box],
    states: dict[str, ProductZoneState],
) -> None:
    for product_id, zone in zones.items():
        image = extract_zone_image(frame, zone)

        if image is None:
            continue

        state = states[product_id]
        state.baseline = image.copy()
        state.change_started_at = None
        state.restored_started_at = None
        state.candidate_session_id = None
        state.picked_up = False

    print("제품 진열 구역 기준 화면 저장 완료")


# ============================================================
# 키포인트 처리
# ============================================================

def extract_wrists(
    keypoints: np.ndarray,
    confidence: np.ndarray | None,
) -> list[Point]:
    """
    COCO Pose 기준:
    9  = 왼쪽 손목
    10 = 오른쪽 손목
    """
    wrists: list[Point] = []

    for wrist_index in (9, 10):
        if wrist_index >= len(keypoints):
            continue

        x, y = keypoints[wrist_index]

        if x <= 0 or y <= 0:
            continue

        if (
            confidence is not None
            and wrist_index < len(confidence)
            and confidence[wrist_index] < 0.35
        ):
            continue

        wrists.append(
            (int(x), int(y))
        )

    return wrists


# ============================================================
# 화면 표시
# ============================================================

def draw_product_zone(
    frame: np.ndarray,
    product_id: str,
    zone: Box,
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

    label = f"{product_id} [{status}]"

    if change_score is not None:
        label += f" diff={change_score:.1f}"

    cv2.putText(
        frame,
        label,
        (x1, max(25, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )


# ============================================================
# 메인
# ============================================================

def main() -> None:
    model = YOLO(MODEL_NAME)
    backend = BackendClient()

    camera = cv2.VideoCapture(
        CAMERA_INDEX,
        cv2.CAP_DSHOW,
    )

    if not camera.isOpened():
        # CAP_DSHOW가 안 되는 환경을 위한 재시도
        camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        raise RuntimeError(
            "웹캠을 열 수 없습니다. "
            "CAMERA_INDEX를 0 또는 1로 바꿔보세요."
        )

    # Track ID → CustomerMemory
    track_to_customer: dict[int, CustomerMemory] = {}

    # 최근 5분 동안 기억 중인 고객
    customer_memories: list[CustomerMemory] = []

    product_states = {
        product_id: ProductZoneState()
        for product_id in PRODUCT_ZONE_RATIOS
    }

    program_started_at = monotonic()
    calibration_completed = False

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("카메라 프레임을 읽지 못했습니다.")
                break

            now = monotonic()

            product_zones = {
                product_id: ratio_to_box(frame, ratios)
                for product_id, ratios
                in PRODUCT_ZONE_RATIOS.items()
            }

            # 프로그램 시작 후 3초 뒤 기준 화면 자동 저장
            if (
                not calibration_completed
                and now - program_started_at
                >= CALIBRATION_DELAY_SECONDS
            ):
                calibrate_product_zones(
                    frame,
                    product_zones,
                    product_states,
                )

                calibration_completed = True

            results = model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                conf=0.45,
                verbose=False,
            )

            result = results[0]
            annotated_frame = result.plot()

            visible_track_ids: set[int] = set()
            active_session_ids: set[int] = set()

            track_wrists: dict[int, list[Point]] = {}

            boxes = result.boxes

            if (
                boxes is not None
                and boxes.id is not None
                and len(boxes) > 0
            ):
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

                visible_track_ids = set(track_ids)

                keypoints_xy: np.ndarray | None = None
                keypoints_conf: np.ndarray | None = None

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
                        keypoints_conf = (
                            result.keypoints.conf
                            .cpu()
                            .numpy()
                        )

                # 이미 매칭된 Track ID의 세션을 먼저 활성 세션에 등록
                for track_id in track_ids:
                    existing = track_to_customer.get(track_id)

                    if existing is not None:
                        active_session_ids.add(
                            existing.session_id
                        )

                for index, (track_id, person_box) in enumerate(
                    zip(track_ids, coordinates)
                ):
                    appearance = extract_appearance(
                        frame,
                        person_box,
                    )

                    customer = track_to_customer.get(track_id)

                    if customer is None and appearance is not None:
                        recent_customer, score = find_recent_customer(
                            appearance=appearance,
                            memories=customer_memories,
                            active_session_ids=active_session_ids,
                            now=now,
                        )

                        if recent_customer is not None:
                            customer = recent_customer

                            print(
                                f"기존 고객 복구: "
                                f"Track {track_id} → "
                                f"Session {customer.session_id} "
                                f"(유사도 {score:.2f})"
                            )

                        else:
                            try:
                                response = (
                                    backend.create_or_get_session(
                                        camera_id=CAMERA_ID,
                                        track_id=track_id,
                                    )
                                )

                                session_id = get_session_id(
                                    response
                                )

                                customer = CustomerMemory(
                                    session_id=session_id,
                                    last_seen_at=now,
                                    appearance=appearance.copy(),
                                )

                                customer_memories.append(
                                    customer
                                )

                                print(
                                    f"새 고객 생성: "
                                    f"Track {track_id} → "
                                    f"Session {session_id}"
                                )

                            except (
                                requests.RequestException,
                                KeyError,
                                ValueError,
                            ) as error:
                                print(
                                    "고객 세션 생성 실패:",
                                    error,
                                )

                        if customer is not None:
                            track_to_customer[track_id] = customer

                    if customer is None:
                        continue

                    customer.last_seen_at = now
                    active_session_ids.add(customer.session_id)

                    if appearance is not None:
                        # 한 프레임 값으로 크게 바뀌지 않도록
                        # 기존 특징과 조금씩 섞는다.
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
                            keypoints_conf is not None
                            and index < len(keypoints_conf)
                        ):
                            confidence = keypoints_conf[index]

                        wrists = extract_wrists(
                            keypoints_xy[index],
                            confidence,
                        )

                        track_wrists[track_id] = wrists

                        for wrist in wrists:
                            cv2.circle(
                                annotated_frame,
                                wrist,
                                7,
                                (255, 255, 255),
                                -1,
                            )

                    center_x, center_y = box_center(person_box)

                    cv2.putText(
                        annotated_frame,
                        (
                            f"Track {track_id} / "
                            f"Session {customer.session_id}"
                        ),
                        (center_x - 100, max(30, center_y)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (255, 255, 255),
                        2,
                    )

            # 5분이 지난 고객 기억 삭제
            customer_memories[:] = [
                memory
                for memory in customer_memories
                if (
                    now - memory.last_seen_at
                    <= SESSION_TTL_SECONDS
                )
            ]

            valid_session_ids = {
                memory.session_id
                for memory in customer_memories
            }

            # 만료된 Track 매핑 제거
            track_to_customer = {
                track_id: memory
                for track_id, memory
                in track_to_customer.items()
                if memory.session_id in valid_session_ids
            }

            # ====================================================
            # 제품 집기 판정
            # ====================================================

            for product_id, zone in product_zones.items():
                state = product_states[product_id]

                current_zone_image = extract_zone_image(
                    frame,
                    zone,
                )

                change_score: float | None = None

                if (
                    state.baseline is not None
                    and current_zone_image is not None
                ):
                    change_score = calculate_zone_change(
                        state.baseline,
                        current_zone_image,
                    )

                touching_sessions: list[int] = []

                for track_id, wrists in track_wrists.items():
                    customer = track_to_customer.get(track_id)

                    if customer is None:
                        continue

                    wrist_is_near = any(
                        point_inside_box(
                            wrist,
                            zone,
                            margin=35,
                        )
                        for wrist in wrists
                    )

                    if wrist_is_near:
                        touching_sessions.append(
                            customer.session_id
                        )

                # 아직 제품이 집힌 상태가 아닐 때
                if not state.picked_up:
                    if (
                        touching_sessions
                        and change_score is not None
                        and change_score
                        >= ZONE_CHANGE_THRESHOLD
                    ):
                        if state.change_started_at is None:
                            state.change_started_at = now
                            state.candidate_session_id = (
                                touching_sessions[0]
                            )

                        changed_duration = (
                            now - state.change_started_at
                        )

                        cooldown_finished = (
                            now - state.last_pickup_at
                            >= PICKUP_COOLDOWN_SECONDS
                        )

                        if (
                            changed_duration
                            >= PICKUP_CONFIRM_SECONDS
                            and cooldown_finished
                            and state.candidate_session_id
                            is not None
                        ):
                            try:
                                backend.add_interaction(
                                    customer_session_id=(
                                        state.candidate_session_id
                                    ),
                                    product_id=product_id,
                                    interaction_type="PICKED_UP",
                                )

                                state.picked_up = True
                                state.last_pickup_at = now
                                state.change_started_at = None

                                print(
                                    f"실제 집기 감지: "
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

                    else:
                        # 손이 가까이 있지 않거나
                        # 화면 변화가 충분하지 않으면 초기화
                        state.change_started_at = None
                        state.candidate_session_id = None

                # 이미 집힌 상태일 때
                else:
                    if (
                        change_score is not None
                        and change_score
                        <= ZONE_RESTORE_THRESHOLD
                    ):
                        if state.restored_started_at is None:
                            state.restored_started_at = now

                        if (
                            now - state.restored_started_at
                            >= ZONE_RESTORE_SECONDS
                        ):
                            state.picked_up = False
                            state.restored_started_at = None
                            state.candidate_session_id = None

                            print(
                                f"{product_id}가 진열 위치로 "
                                "돌아와 다시 감지 가능"
                            )

                    else:
                        state.restored_started_at = None

                draw_product_zone(
                    annotated_frame,
                    product_id,
                    zone,
                    state,
                    change_score,
                )

            # ====================================================
            # 안내 문구
            # ====================================================

            if not calibration_completed:
                remaining = max(
                    0.0,
                    CALIBRATION_DELAY_SECONDS
                    - (now - program_started_at),
                )

                cv2.putText(
                    annotated_frame,
                    (
                        "Keep bags on shelf - "
                        f"calibrating {remaining:.1f}s"
                    ),
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            else:
                cv2.putText(
                    annotated_frame,
                    "C: Recalibrate | Q: Quit",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            cv2.imshow(
                "MCM AR Fitting Vision",
                annotated_frame,
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            if key == ord("c"):
                calibrate_product_zones(
                    frame,
                    product_zones,
                    product_states,
                )

                calibration_completed = True

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()