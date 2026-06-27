# praat-mcp (Praat ↔ Claude 연동)

## 1. 이게 뭐예요?

이 프로그램은 음성언어학 분석 도구 Praat(프라트) 를, Claude 같은 LLM에서 바로 실행할 수 있게 연결해주는 도구입니다. 기술적으로는 MCP(Model Context Protocol) 서버입니다.

### Praat을 직접 쓸 때 vs 이 MCP로 쓸 때

Praat 자체로도 모든 분석이 가능합니다. 이 MCP는 그 위에 "Claude와의 대화"라는 인터페이스를 하나 더 얹어서, 아래 같은 부분을 더 편하게 만들어 줍니다.

| 작업 | Praat 직접 사용 | 이 MCP(+Claude) 사용 |
| --- | --- | --- |
| 분석 실행 | 메뉴 클릭 → 객체 선택 → 명령 실행을 직접 반복 | "이 음성 jitter/shimmer 분석해줘"처럼 자연어로 요청 → Claude가 알맞은 스크립트를 찾아 실행 |
| 스크립트 작성/수정 | Praat 스크립팅 문법을 직접 익혀서 작성 | 필요한 분석을 말로 설명하면 Claude가 스크립트를 작성/수정해서 제안 (직접 코딩하지 않아도 됨) |
| 세부 파라미터 | 설정 창에 값을 직접 입력 | 피치 범위, CPPS 옵션처럼 세부 설정이 필요한 스크립트는 Claude가 먼저 어떤 값을 쓸지 물어본 뒤 실행 |
| 결과 확인 | Info 창/저장된 txt를 직접 열어서 읽고 해석 | 결과를 Claude가 같이 읽고 대화로 요약·해석해 줌 (txt 파일은 result 폴더에 그대로도 저장됨) |
| 그림/소리 결과물 | Picture 창에 그려서 따로 저장 | 스크립트가 만든 PNG/WAV 같은 산출물을 대화 안에서 바로 같이 받아볼 수 있음 |
| 대량 배치 처리 | 헤드리스 스크립트를 직접 돌리고 콘솔/로그를 계속 들여다봐야 함 | 오래 걸리는 배치는 백그라운드로 시작해두고, 진행 상태(running/done/error/timeout)를 물어보면 Claude가 확인해 알려줌 |

위 기능들은 아래 9개의 MCP 도구로 동작합니다.

- `list_praat_scripts` / `get_praat_script` / `get_praat_script_params` : 사용 가능한 스크립트 탐색, 본문 확인, 필요한 파라미터 확인
- `run_praat_script` / `run_praat_script_background` / `get_praat_job_status` : 즉시 실행 또는 백그라운드 실행, 백그라운드 작업 상태 조회
- `create_praat_script` / `update_praat_script` / `delete_praat_script` : 스크립트 생성·수정·삭제 (수정/삭제 시 자동 백업)

"어떤 스크립트를 쓸지", "파라미터를 어떻게 채울지"는 상황에 맞게 Claude가 판단하거나 사용자에게 먼저 물어봅니다.

## 2. 준비물(한 번만 설치)

아래 두 가지가 PC에 설치되어 있어야 합니다.

| 준비물           | 왜 필요해요?    | 설치            |
| ------------- | ---------- | ------------- |
| Python 3.12.x | 프로그램 실행 환경 | https://www.python.org/ |
| uv            | 패키지/실행 도구  | https://www.0x00.kr/development/python/python-uv-simple-usage-and-example |


설치 확인 방법(Windows cmd에서 실행):

1. python -V → 버전이 나오면 OK
2. uv -V → 버전이 나오면 OK

. 폴더 준비(프로젝트 폴더 안)
프로젝트 폴더(예: C:\Users\Your-name\Desktop\mcp-praat) 안에 아래 폴더를 만듭니다.

script : Praat 스크립트(.praat) 넣는 폴더
result : 분석 결과(.txt)가 저장되는 폴더
결과:

mcp-praat/
 ├─ main.py
 ├─ praat_analysis.py
 ├─ 그 외 다양한 .py 파일들...
 ├─ uv.lock
 ├─ pyproject.toml
 ├─ .python-version
 ├─ .venv/
 ├─ script/
 └─ result/

4. .env 파일 만들기(필수)
프로젝트 폴더(mcp-praat) 안에 .env 파일을 만듭니다. 확장자 없고, 파일 이름이 .env 입니다.

결과:

mcp-praat/
 ├─ main.py
 ├─ praat_analysis.py
 ├─ 그 외 다양한 .py 파일들...
 ├─ uv.lock
 ├─ pyproject.toml
 ├─ .python-version
 ├─ .env
 ├─ .venv/
 ├─ script/
 └─ result/
.env에 들어갈 변수
변수	의미
MCP_ROOT_DIR	프로젝트 폴더 경로
PRAAT_EXE_DIR	Praat.exe가 있는 폴더 경로 (또는 Praat.exe 전체 경로도 동작하도록 되어 있음)
SCRIPT_DIR	.praat 스크립트 폴더 경로
RESULT_DIR	결과 가 저장될 폴더 경로.txt
Windows에서는 \ 때문에 헷갈리기 쉬우니, 아래 예시처럼 따옴표로 감싸기를 권장합니다.

MCP_ROOT_DIR="C:\Users\Your-name\Desktop\mcp-praat"
PRAAT_EXE_DIR="C:\Program Files\Praat"
SCRIPT_DIR="C:\Users\Your-name\Desktop\mcp-praat\script"
RESULT_DIR="C:\Users\Your-name\Desktop\mcp-praat\result"
Praat가 설치된 위치가 다르면 PRAAT_EXE_DIR만 본인 PC에 맞게 바꾸면 됩니다.
RESULT_DIR에 \result 같이 중복 슬래시는 넣지 마세요. 위 예시처럼 한 번만 쓰면 됩니다.

5. Claude Desktop에 연결하기
Claude Desktop 설정 파일을 수정해서, Claude가 이 프로그램을 실행하도록 연결합니다.

설정 파일: claude_desktop_config.json

Claude Desktop에서 MCP 서버 설정을 추가합니다. 예시는 아래와 같습니다.

주의

--directory에는 반드시 프로젝트 폴더의 절대경로가 들어가야 합니다.
Windows 경로는 \ 때문에 오류가 날 수 있으니, 예시처럼 그대로 작성하세요.
{
  "mcpServers": {
    "praat-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\C:\Users\Your-name\Desktop\mcp-praat",
        "run",
        "main.py"
      ]
    }
  },
  "preferences": {
    "coworkScheduledTasksEnabled": false,
    "ccdScheduledTasksEnabled": true,
    "sidebarMode": "chat",
    "coworkWebSearchEnabled": true,
    "epitaxyPrefs": {
      "starred-local-code-sessions": [],
      "starred-cowork-spaces": [],
      "starred-session-groups": [],
      "dframe-local-slice": {
        "pinnedOrder": [],
        "customGroupAssignments": {},
        "customGroupOrder": {}
      }
    }
  }
}
설정 후 Claude Desktop을 완전히 종료했다가 다시 실행하세요.

6. 사용 방법(실제 분석)
Claude에게 음성 파일의 절대경로를 알려주고 분석을 요청하면 됩니다.


plaintext
C:\Users\Your-name\Desktop\audio\sample.wav 이 파일을 분석해줘.
jitter / shimmer / HNR 분석해줘.
가능한 스크립트 목록을 보여주고 적절한 걸로 실행해줘.

다음 경로의 음성 파일에서 CPPs를 추출해줘.
파일 경로 : C:\Users\Your-name\Desktop\mcp-praat\audio
파라미터 설정:
  - Pitch Floor: 60 Hz
  - Pitch Ceiling: 330 Hz
  - Time Step: 0.002s
  - Max Frequency: 5000 Hz
  - Pre-emphasis: 50 Hz
  - Smoothing: Straight, Robust

CPPs 배치 분석을 위한 Praat 스크립트를 작성해줘.
조건:
  - 입력 폴더의 모든 .wav 파일 처리
  - Watts et al. (2017) 표준 파라미터 적용
  - 결과를 탭 구분 텍스트 파일로 출력
완성된 스크립트를 cpps_batch.praat 파일로 저장해줘.
결과는 Claude가 보여주고 동시에 result 폴더에 .txt 파일로 저장됩니다