from __future__ import annotations

import cv2
import requests
from ultralytics import YOLO

from backend_client import BackendClient


CAMERA_ID = "CAMERA_01"


def main() -> None:
    model = YOLO("yolo26n.pt")
    backend = BackendClient()

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        raise RuntimeError("웹캠을 열 수 없습니다.")

    # 카메라 Track ID → Spring Boot CustomerSession ID
    track_to_session: dict[int, int] = {}

    # 현재 화면에서 가장 중심에 있는 고객
    current_track_id: int | None = None

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("카메라 프레임을 읽지 못했습니다.")
                break

            results = model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=[0],
                conf=0.5,
                verbose=False,
            )

            result = results[0]
            annotated_frame = result.plot()

            boxes = result.boxes

            if boxes is not None and boxes.id is not None:
                track_ids = boxes.id.int().cpu().tolist()
                coordinates = boxes.xyxy.cpu().tolist()

                frame_center_x = frame.shape[1] / 2

                closest_track_id: int | None = None
                closest_distance = float("inf")

                for track_id, box in zip(track_ids, coordinates):
                    x1, y1, x2, y2 = box
                    person_center_x = (x1 + x2) / 2
                    distance = abs(person_center_x - frame_center_x)

                    # 아직 백엔드 세션이 없는 Track ID면 생성
                    if track_id not in track_to_session:
                        try:
                            session = backend.create_or_get_session(
                                camera_id=CAMERA_ID,
                                track_id=track_id,
                            )

                            session_id = int(
                                session["customerSessionId"]
                            )

                            track_to_session[track_id] = session_id

                            print(
                                f"Track {track_id} "
                                f"→ CustomerSession {session_id}"
                            )

                        except requests.RequestException as error:
                            print(
                                "고객 세션 생성 API 호출 실패:",
                                error,
                            )

                    # 화면 중앙에 가장 가까운 사람을 현재 고객으로 선택
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_track_id = track_id

                current_track_id = closest_track_id

            else:
                current_track_id = None

            # 화면 안내 문구
            cv2.putText(
                annotated_frame,
                "A: BAG_A | B: BAG_B | Q: Quit",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
            )

            if current_track_id is not None:
                session_id = track_to_session.get(current_track_id)

                cv2.putText(
                    annotated_frame,
                    (
                        f"Current Track: {current_track_id} "
                        f"/ Session: {session_id}"
                    ),
                    (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            cv2.imshow(
                "MCM Customer Tracking",
                annotated_frame,
            )

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            if current_track_id is None:
                continue

            customer_session_id = track_to_session.get(
                current_track_id
            )

            if customer_session_id is None:
                continue

            try:
                if key == ord("a"):
                    backend.add_interaction(
                        customer_session_id=customer_session_id,
                        product_id="BAG_A",
                    )

                    print(
                        f"CustomerSession {customer_session_id}"
                        "에 BAG_A 저장 완료"
                    )

                elif key == ord("b"):
                    backend.add_interaction(
                        customer_session_id=customer_session_id,
                        product_id="BAG_B",
                    )

                    print(
                        f"CustomerSession {customer_session_id}"
                        "에 BAG_B 저장 완료"
                    )

            except requests.RequestException as error:
                print(
                    "제품 상호작용 API 호출 실패:",
                    error,
                )

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()