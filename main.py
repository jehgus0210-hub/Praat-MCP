from fastmcp import FastMCP
from fastmcp.utilities.types import Image, Audio
from typing import Optional

from logger import Logger
from boot import boot_up

import praat_analysis
import praat_script
import praat_jobs


logger = Logger()
cfg = boot_up(logger)
mcp = FastMCP(name="praat-mcp")


def _attach_media(result: dict):
    """
    result["media"]에 담긴 이미지/오디오 파일을 fastmcp Image/Audio 콘텐츠로 변환해
    텍스트 결과와 함께 반환한다. media가 없으면 기존처럼 dict만 반환(하위 호환).
    """
    media = result.pop("media", None) or []
    if not media:
        return result

    content = [result]
    for m in media:
        if m["kind"] == "image":
            content.append(Image(path=m["path"]))
        elif m["kind"] == "audio":
            content.append(Audio(path=m["path"]))
    return content

@mcp.tool()
def list_praat_scripts(include_source: bool = False, max_chars: int = 8000) -> dict:
    """
    지정된 script_dir에 있는 스크립트 조회.
    - include_source=True 면 스크립트 본문까지 포함해 모델 컨텍스트로 제공.
    
    scripts: [{id, filename, path, source?}]
    """

    return praat_analysis.view_list(cfg, include_source, max_chars)

@mcp.tool()
def get_praat_script(script_id: str, max_chars: int = 20000) -> dict:
    """
    단일 스크립트 본문 제공.
    - script_id: 스크립트 ID
    
    - LLM에 컨텍스트를 제공
    """

    return praat_analysis.get(cfg, script_id, max_chars)

@mcp.tool()
def get_praat_script_params(script_id: str) -> dict:
    """
    스크립트의 form~endform 블록을 파싱해 파라미터 목록을 구조화해서 제공.
    - auto_filled_by_tool: 앞쪽 1~2개 필드는 run_praat_script(_background) 호출 시
      audio_path/out_file로 자동 채워짐
    - needs_args: 나머지 필드는 args 리스트로 순서대로(args_index) 전달해야 함
    - needs_args가 비어있지 않은 스크립트를 실행하기 전에는 먼저 이 도구로 확인하고,
      각 파라미터 값을 사용자에게 물어본 뒤 run_praat_script(_background)를 호출할 것
    """

    return praat_analysis.get_params(cfg, script_id)

@mcp.tool()
def run_praat_script(
    script_id: str,
    audio_path: str,
    args: Optional[list[str]] = None,
    include_source: bool = True,
    source_max_chars: int = 8000,
    timeout_sec: int = 300,
):
    """
    Praat.exe --run --no-pref-files <script> <audio_path> <output_file> [args...]

    - 결과는 RESULT_DIR/<job_id>.txt 단일 파일
    - 결과 txt 내용(result_text)을 그대로 반환
    - include_source=True면 실행 응답에 스크립트 본문도 포함(컨텍스트 제공)
    - timeout_sec 안에 끝나지 않으면 강제 종료하고 status="timeout" 반환
    - 스크립트가 실행 중 RESULT_DIR에 PNG/WAV 같은 이미지/오디오 파일을 새로 만들면
      텍스트 결과와 함께 이미지/오디오 콘텐츠로도 반환됨
    - 오래 걸리는 배치 스크립트는 run_praat_script_background를 사용할 것
    - 스크립트에 args로 채워야 하는 파라미터가 있는지 모르겠으면 먼저
      get_praat_script_params로 확인하고, 필요한 값은 사용자에게 물어본 뒤 호출할 것
    """

    result = praat_analysis.run(
        logger, cfg, script_id, audio_path, args, include_source, source_max_chars, timeout_sec
    )
    return _attach_media(result)


@mcp.tool()
def run_praat_script_background(
    script_id: str,
    audio_path: str,
    args: Optional[list[str]] = None,
    timeout_sec: Optional[int] = None,
) -> dict:
    """
    오래 걸리는 Praat 스크립트(대량 배치 등)를 백그라운드로 시작.
    - 즉시 job_id를 반환하며 실행은 계속 진행됨(서버 프로세스가 살아있는 동안 계속 돎)
    - 진행 상태/결과는 get_praat_job_status(job_id)로 확인
    - 짧은 간격으로 같은 대화 턴 안에서 반복 폴링하지 말 것. 대량 배치처럼 오래 걸릴
      작업은 시작만 해두고, 사용자가 나중에 다시 물어볼 때 한 번 확인하면 됨
      (확인 자체를 오래 기다리려면 get_praat_job_status(job_id, wait_sec=...)로
      필요한 만큼 길게 기다렸다가 받을 수도 있음)
    - timeout_sec=None이면 시간제한 없이 실행(장시간 배치 기본값)
    - 스크립트에 args로 채워야 하는 파라미터가 있는지 모르겠으면 먼저
      get_praat_script_params로 확인하고, 필요한 값은 사용자에게 물어본 뒤 호출할 것
    """

    return praat_jobs.start(logger, cfg, script_id, audio_path, args, timeout_sec)


@mcp.tool()
def get_praat_job_status(job_id: str, wait_sec: float = 0):
    """
    run_praat_script_background로 시작한 작업의 상태/결과 조회.
    - status: running | done | error | timeout
    - running이면 elapsed_sec만 포함, 완료 시 stdout/stderr/result_text/media 포함
    - wait_sec>0이면 그 시간(초) 동안 서버가 내부적으로 기다렸다가(먼저 끝나면 즉시)
      반환함. 오래 걸리는 배치를 짧은 간격으로 같은 대화 턴에서 반복 호출하지 말고,
      한 번 확인하고 아직 running이면 사용자에게 나중에 다시 물어볼 때 확인할 것
    """

    result = praat_jobs.status(cfg, job_id, wait_sec)
    return _attach_media(result)

@mcp.tool()
def update_praat_script(script_id: str, content: str, create_backup: bool = True) -> dict:
    """
    기존 Praat 스크립트 내용 업데이트.
    - script_id: 스크립트 ID (예: 'jitter-shimmer')
    - content: 새로운 스크립트 내용
    - create_backup: 백업 파일 생성 여부 (.praat.bak)
    """
    
    return praat_script.update(logger, cfg.script_dir, script_id, content, create_backup)

@mcp.tool()
def create_praat_script(filename: str, content: str, overwrite: bool = False) -> dict:
    """
    새 Praat 스크립트 생성.
    - filename: 파일명 (자동으로 .praat 확장자 추가)
    - content: 스크립트 내용
    - overwrite: 기존 파일 덮어쓰기 허용 여부
    """

    return praat_script.create(logger, cfg.script_dir, filename, content, overwrite)

@mcp.tool()
def delete_praat_script(script_id: str, create_backup: bool = True) -> dict:
    """
    Praat 스크립트 삭제.
    - script_id: 스크립트 ID
    - create_backup: 삭제 전 백업 생성 여부 (.praat.deleted)
    """

    return praat_script.delete(logger, cfg.script_dir, script_id, create_backup)

if __name__ == "__main__":
    mcp.run(transport="stdio")
