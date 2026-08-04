# MCM AR Fitting

카메라로 고객을 익명 추적하고, 고객이 관심을 보인 제품을 저장한 뒤 AR 피팅에 활용하는 프로젝트입니다.

## 프로젝트 구조

```text
mcm-ar-fitting/
├─ backend/   Spring Boot 백엔드
└─ vision/    Python 컴퓨터 비전

실행 환경
Java 17 이상
Python 3.12 권장
웹캠 필요
1. 프로젝트 다운로드
git clone 깃허브-저장소-주소
cd mcm-ar-fitting
2. 백엔드 실행

Windows 기준:

cd backend
.\gradlew.bat bootRun

IntelliJ에서 ArFittingApplication을 직접 실행해도 됩니다.

백엔드는 기본적으로 아래 주소에서 실행됩니다.

http://localhost:8080
3. Python 가상환경 생성

새 터미널을 열고 실행합니다.

cd vision

python -m venv .venv
.\.venv\Scripts\Activate.ps1

PowerShell 실행 정책 오류가 발생하면:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
4. Python 패키지 설치
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
5. 컴퓨터 비전 프로그램 실행

백엔드를 먼저 실행한 상태에서:

python main.py

종료하려면 카메라 창을 선택한 뒤 Q 키를 누릅니다.