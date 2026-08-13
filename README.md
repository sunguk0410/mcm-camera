# MCM AR Fitting

카메라로 고객을 추적하고 상품 구역 상호작용을 감지해 배포 API로 전송하는 컴퓨터 비전 프로젝트입니다.

## 실행 환경

- Python 3.12 권장
- 웹캠 필요

## 설치 및 실행

```powershell
cd vision
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

카메라 창에서 `Q`를 누르면 프로그램이 종료됩니다.

별도의 로컬 백엔드는 필요하지 않습니다. 프로그램은 다음 배포 API를 직접 사용합니다.

```text
https://api.mcm-showcase.com
```

상품 구역 상호작용은 `POST /api/zone-interactions`로 전송됩니다. `vision/config.py`의 `FLOOR_CODE`와 `PRODUCT_ZONE_RATIOS`를 실제 매장 설정에 맞게 수정하세요. 현재 상품 ID(`BAG_A`, `BAG_B`)가 `categoryCode`로 사용됩니다.

## 주의사항

- `.venv`와 YOLO 모델 파일은 Git에 포함되지 않습니다.
- 카메라 위치가 바뀌면 `PRODUCT_ZONE_RATIOS`를 다시 조정해야 합니다.
