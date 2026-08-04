from __future__ import annotations

import cv2
from ultralytics import YOLO


def main() -> None:
    # 처음 실행할 때 모델 파일이 자동으로 내려받아질 수 있음
    model = YOLO("yolo26n.pt")

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        raise RuntimeError("웹캠을 열 수 없습니다.")

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

            cv2.imshow(
                "MCM Customer Tracking",
                annotated_frame,
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()