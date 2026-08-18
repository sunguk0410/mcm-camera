# main.py

from __future__ import annotations

import cv2
from ultralytics import YOLO

from backend_client import BackendClient
from config import (
    BACKEND_BASE_URL,
    CAMERA_INDEX,
    MODEL_NAME,
    PERSON_CONFIDENCE,
)
from spatial_interaction import SpatialInteractionTracker


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

    backend = BackendClient(BACKEND_BASE_URL)
    interaction_tracker = SpatialInteractionTracker(backend)

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

            interaction_tracker.update(
                frame=frame,
                output_frame=output_frame,
                result=result,
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

    finally:
        interaction_tracker.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
