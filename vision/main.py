# main.py

from __future__ import annotations

import cv2
from ultralytics import YOLO

from backend_client import BackendClient
from config import (
    CAMERA_INDEX,
    MODEL_NAME,
    PERSON_CONFIDENCE,
)
from customer_tracker import CustomerTracker
from pickup_detector import PickupDetector


def open_camera() -> cv2.VideoCapture:
    camera = cv2.VideoCapture(
        CAMERA_INDEX,
        cv2.CAP_DSHOW,
    )

    if not camera.isOpened():
        camera.release()

        camera = cv2.VideoCapture(
            CAMERA_INDEX
        )

    if not camera.isOpened():
        raise RuntimeError(
            "웹캠을 열 수 없습니다. "
            "config.py의 CAMERA_INDEX를 "
            "0 또는 1로 바꿔보세요."
        )

    return camera


def main() -> None:
    model = YOLO(MODEL_NAME)

    backend = BackendClient()

    customer_tracker = CustomerTracker(
        backend=backend
    )

    pickup_detector = PickupDetector(
        backend=backend
    )

    camera = open_camera()

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print(
                    "카메라 프레임을 "
                    "읽지 못했습니다."
                )
                break

            results = model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                conf=PERSON_CONFIDENCE,
                verbose=False,
            )

            result = results[0]

            # YOLO 탐지 결과가 그려진 화면
            output_frame = result.plot()

            tracking_output = (
                customer_tracker.update(
                    frame=frame,
                    result=result,
                )
            )

            customer_tracker.draw_customer_labels(
                frame=output_frame,
                result=result,
            )

            customer_tracker.draw_wrists(
                frame=output_frame,
                track_wrists=(
                    tracking_output.track_wrists
                ),
            )

            pickup_detector.update(
                frame=frame,
                output_frame=output_frame,
                track_to_customer=(
                    tracking_output
                    .track_to_customer
                ),
                track_wrists=(
                    tracking_output
                    .track_wrists
                ),
            )

            cv2.imshow(
                "MCM AR Fitting Vision",
                output_frame,
            )

            key = (
                cv2.waitKey(1)
                & 0xFF
            )

            if key == ord("q"):
                break

            if key == ord("c"):
                pickup_detector.calibrate(
                    frame
                )

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()