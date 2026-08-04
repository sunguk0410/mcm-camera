# MCM AR Fitting

카메라로 고객을 익명 추적하고, 고객이 관심을 보인 제품을 저장한 뒤 AR 피팅에 활용하는 프로젝트입니다.

## 프로젝트 구조

```text
mcm-ar-fitting/
├─ backend/   Spring Boot 백엔드
└─ vision/    Python 컴퓨터 비전
```

## 실행 환경

- Java 17 이상
- Python 3.12 권장
- 웹캠 필요

## 1. 프로젝트 다운로드

```bash
git clone https://github.com/sunguk0410/mcm-ar-fitting.git
cd mcm-ar-fitting
```

## 2. 백엔드 실행

Windows 기준:

```powershell
cd backend
.\gradlew.bat bootRun
```

또는 IntelliJ에서 `ArFittingApplication`을 직접 실행해도 됩니다.

백엔드는 기본적으로 아래 주소에서 실행됩니다.

```text
http://localhost:8080
```

## 3. Python 가상환경 생성

새 터미널을 열고 `vision` 폴더로 이동합니다.

```powershell
cd vision
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

PowerShell 실행 정책 오류가 발생하면 다음 명령어를 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

가상환경이 정상적으로 활성화되면 터미널 앞에 `(.venv)`가 표시됩니다.

## 4. Python 패키지 설치

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 5. 컴퓨터 비전 프로그램 실행

Spring Boot 백엔드가 실행 중인 상태에서 실행합니다.

```powershell
python main.py
```

카메라 창을 선택한 뒤 `Q` 키를 누르면 프로그램이 종료됩니다.

## 실행 순서

1. 프로젝트 다운로드
2. Spring Boot 백엔드 실행
3. Python 가상환경 생성 및 활성화
4. Python 패키지 설치
5. `main.py` 실행

## 주의사항

- `.venv` 폴더는 GitHub에 올리지 않습니다.
- 각 개발자는 프로젝트를 받은 뒤 가상환경을 새로 생성해야 합니다.
- Python 프로그램 실행 전에 백엔드가 먼저 실행되어 있어야 합니다.
