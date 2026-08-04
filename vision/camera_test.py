import cv2


def main() -> None:
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        raise RuntimeError("웹캠을 열 수 없습니다.")

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("웹캠 화면을 읽지 못했습니다.")
                break

            cv2.imshow("Camera Test", frame)

            # Q 키를 누르면 종료
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()