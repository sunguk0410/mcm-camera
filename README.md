# MCM Camera

천장(약 2.5m)에 설치한 카메라 한 대로 한 명의 고객을 추적하는 시연용 프로그램입니다.

- 사람이 처음 감지되면 `POST /api/customer-sessions`
- 왼쪽 2×2 존에서 나가면 `POST /api/zone-interactions`
- 오른쪽 AR 피팅 존에 3초 이상 서 있으면 `PATCH /api/ar-sessions/{id}/customer-session`
- 사람이 화면에서 2초 이상 사라지면 현재 존을 기록하고 CustomerSession 종료

## 설정

실행 전에 [vision/config.py](vision/config.py)의 `ZONE_RATIOS`와 `ZONE_METADATA`를 실제 바닥 배치와 서버 코드에 맞게 수정하세요. 좌표는 `(left, top, right, bottom)`이며 화면 크기에 대한 0~1 비율입니다.

카메라는 AR 피팅 존에 3초 이상 머물면 서버에서 최신 활성 ARSession을 조회한 뒤 현재 CustomerSession과 연결합니다. Spring 서버에는 `GET /api/ar-sessions/active/latest`가 있어야 합니다.

```powershell
$env:MCM_BACKEND_URL='https://api.mcm-showcase.com'
```

활성 ARSession이 없거나 요청이 실패하면 1초 간격으로 다시 조회합니다.

## 실행

```powershell
cd vision
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

화면의 파란 사각형은 상품 존, 자홍색 사각형은 AR 피팅 존, 빨간 점은 존 판정에 사용하는 사람의 바닥 접점입니다. 종료는 `Q`입니다.

## 테스트

```powershell
cd vision
python -m unittest -v test_spatial_interaction.py
```
