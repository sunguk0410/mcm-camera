# config.py

CAMERA_ID = "CAMERA_01"
CAMERA_INDEX = 0

# YOLO Pose 모델
MODEL_NAME = "yolo26n-pose.pt"

# 사람 탐지 신뢰도
PERSON_CONFIDENCE = 0.60

# 화면 전체 대비 너무 작은 사람은 무시
MIN_PERSON_AREA_RATIO = 0.05

# 사람이 사라져도 기존 고객으로 기억할 시간
SESSION_TTL_SECONDS = 5 * 60

# 옷 색상 유사도
# 값이 높을수록 더 비슷해야 같은 사람으로 판단
APPEARANCE_MATCH_THRESHOLD = 0.60

# 프로그램 시작 후 제품 기준 화면 저장까지 대기
CALIBRATION_DELAY_SECONDS = 3.0

# 제품 구역 변화 기준
ZONE_CHANGE_THRESHOLD = 22.0

# 변화가 일정 시간 지속돼야 실제 집기로 판단
PICKUP_CONFIRM_SECONDS = 0.8

# 같은 제품의 중복 저장 방지 시간
PICKUP_COOLDOWN_SECONDS = 10.0

# 가방이 다시 원래 위치로 돌아왔다고 판단하는 기준
ZONE_RESTORE_THRESHOLD = 12.0

# 복귀 상태 유지 시간
ZONE_RESTORE_SECONDS = 1.0

# 제품 진열 구역
#
# 형식:
# (왼쪽 비율, 위쪽 비율, 오른쪽 비율, 아래쪽 비율)
#
# 실제 카메라 화면에 맞게 수정해야 함
PRODUCT_ZONE_RATIOS = {
    "BAG_A": (0.03, 0.25, 0.35, 0.90),
    "BAG_B": (0.65, 0.25, 0.97, 0.90),
}