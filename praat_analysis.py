import subprocess, os, uuid, re
from typing import Optional
from encoding import _decode_utf16_bytes, _read_script_text, discover_scripts
from praat_form import parse_form
from pathlib import Path


DEFAULT_TIMEOUT_SEC = 300

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}

# pause/beginPause는 사람의 클릭을 기다리는 모달이라 --run 헤드리스 실행에서 응답 없이 멈춘다.
_BLOCKING_COMMAND_RE = re.compile(r"^\s*(pause|beginPause)\b", re.MULTILINE)


def find_blocking_commands(source: str) -> list[str]:
    return sorted(set(m.group(1) for m in _BLOCKING_COMMAND_RE.finditer(source)))


def snapshot_files(dir_path: Path) -> dict[Path, float]:
    if not dir_path.exists():
        return {}
    return {p: p.stat().st_mtime for p in dir_path.rglob("*") if p.is_file()}


def collect_new_media(before: dict[Path, float], result_dir: Path, exclude: set[Path]) -> list[dict]:
    after = snapshot_files(result_dir)
    media = []
    for p, mtime in after.items():
        if p in exclude or (p in before and before[p] == mtime):
            continue
        ext = p.suffix.lower()
        if ext in IMAGE_EXTS:
            media.append({"path": str(p), "kind": "image"})
        elif ext in AUDIO_EXTS:
            media.append({"path": str(p), "kind": "audio"})
    return media


def view_list(cfg, include_source: bool = False, max_chars: int = 8000) -> dict:
    """
    scripts: [{id, filename, path, source?}]
    include_source=True면 스크립트 본문까지 포함해 모델 컨텍스트로 제공.
    """
    scripts = discover_scripts(cfg.script_dir)
    items = []
    for sid, path in sorted(scripts.items()):
        item = {"id": sid, "filename": path.name, "path": str(path)}
        if include_source:
            src = _read_script_text(path)
            if max_chars is not None and len(src) > max_chars:
                src = src[:max_chars] + "\n\n...(truncated)..."
            item["source"] = src
        items.append(item)
    return {"scripts": items}

def get(cfg, script_id: str, max_chars: int = 20000) -> dict:
    """
    단일 스크립트 본문 제공(컨텍스트 제공용).
    """
    scripts = discover_scripts(cfg.script_dir)
    if script_id not in scripts:
        raise ValueError(f"Unknown script_id: {script_id}")

    path = scripts[script_id]
    src = _read_script_text(path)
    if max_chars is not None and len(src) > max_chars:
        src = src[:max_chars] + "\n\n...(truncated)..."

    return {"id": script_id, "filename": path.name, "path": str(path), "source": src}

def get_params(cfg, script_id: str) -> dict:
    """
    스크립트의 form~endform 블록을 파싱해 파라미터 목록을 구조화해서 반환.
    - run_praat_script(_background) 호출 시 form의 첫 1~2개 필드는 audio_path/out_file로
      자동 채워지고, 나머지 필드만 args 리스트로 순서대로 전달하면 됨.
    """
    scripts = discover_scripts(cfg.script_dir)
    if script_id not in scripts:
        raise ValueError(f"Unknown script_id: {script_id}")

    path = scripts[script_id]
    src = _read_script_text(path)
    form = parse_form(src)

    if form is None:
        return {"id": script_id, "filename": path.name, "has_form": False, "fields": []}

    input_fields = [f for f in form["fields"] if f.get("is_input")]
    auto_filled = input_fields[:2]
    needs_args = input_fields[2:]
    for i, f in enumerate(needs_args):
        f["args_index"] = i

    fill_sources = ["audio_path", "out_file"]
    return {
        "id": script_id,
        "filename": path.name,
        "has_form": True,
        "title": form["title"],
        "fields": form["fields"],
        "auto_filled_by_tool": [
            {"label": f["label"], "variable": f["variable"], "filled_with": fill_sources[i]}
            for i, f in enumerate(auto_filled)
        ],
        "needs_args": needs_args,
    }

def run(
    logger,
    cfg,
    script_id: str,
    audio_path: str,
    args: Optional[list[str]] = None,
    include_source: bool = True,
    source_max_chars: int = 8000,
    timeout_sec: Optional[int] = DEFAULT_TIMEOUT_SEC,
) -> dict:
    """
    Praat.exe --run --no-pref-files <script> <audio_path> <output_file> [args...]

    - 결과는 RESULT_DIR/<job_id>.txt 단일 파일
    - 결과 txt 내용(result_text)을 그대로 반환
    - include_source=True면 실행 응답에 스크립트 본문도 포함(컨텍스트 제공)
    - timeout_sec 초과 시 프로세스를 강제 종료하고 status="timeout"으로 반환
    - 실행 중 RESULT_DIR에 새로 생긴 이미지/오디오 파일은 media 목록으로 함께 반환
    """
    if args is None:
        args = []

    scripts = discover_scripts(cfg.script_dir)
    if script_id not in scripts:
        raise ValueError(f"Unknown script_id: {script_id}")

    script_path = scripts[script_id]
    script_source = _read_script_text(script_path)

    blocking = find_blocking_commands(script_source)
    if blocking:
        raise ValueError(
            f"스크립트에 헤드리스 실행에서 멈출 수 있는 명령이 있습니다: {', '.join(blocking)}. "
            "pause/beginPause를 제거한 뒤 다시 시도하세요."
        )

    job_id = uuid.uuid4().hex

    # ✅ 폴더가 아니라 단일 txt 파일
    out_file = (cfg.result_dir / f"{job_id}.txt").resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # PoC: 상대/절대 허용 (검증 없음)
    audio_p = Path(os.path.expandvars(os.path.expanduser(audio_path))).resolve()

    # UTF-16 고정 목표: --utf8 사용 금지 + pref 영향 제거
    cmd = [
        str(cfg.praat_exe_path),
        "--run",
        "--no-pref-files",
        str(script_path),
        str(audio_p),
        str(out_file),
        *args,
    ]

    logger.info("RUN job=%s script=%s audio=%s out=%s", job_id, script_id, audio_p, out_file)

    before = snapshot_files(cfg.result_dir)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=False,     # 바이트로 받고 UTF-16로 직접 디코드
            shell=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as e:
        logger.error("TIMEOUT job=%s script=%s after %ss", job_id, script_id, timeout_sec)
        return {
            "job_id": job_id,
            "output_file": str(out_file),
            "status": "timeout",
            "exit_code": None,
            "stdout": _decode_utf16_bytes(e.stdout or b""),
            "stderr": _decode_utf16_bytes(e.stderr or b""),
            "output": None,
            "result_text": None,
            "script": None,
            "media": [],
            "cmd": cmd,
        }

    stdout = _decode_utf16_bytes(proc.stdout or b"")
    stderr = _decode_utf16_bytes(proc.stderr or b"")

    # 결과 파일 내용(그대로)
    result_text = None
    output_meta = None
    if out_file.exists() and out_file.is_file():
        raw = out_file.read_bytes()
        result_text = _decode_utf16_bytes(raw)

        output_meta = {
            "filename": out_file.name,
            "path": str(out_file),
            "mime_type": "text/plain",
            "size": out_file.stat().st_size,
        }

    # 스크립트 컨텍스트 포함
    script_info = None
    if include_source:
        src = script_source
        if source_max_chars is not None and len(src) > source_max_chars:
            src = src[:source_max_chars] + "\n\n...(truncated)..."
        script_info = {"id": script_id, "filename": script_path.name, "path": str(script_path), "source": src}

    media = collect_new_media(before, cfg.result_dir, exclude={out_file})

    return {
        "job_id": job_id,
        "output_file": str(out_file),
        "status": "done" if proc.returncode == 0 else "error",
        "exit_code": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "output": output_meta,
        "result_text": result_text,
        "script": script_info,
        "media": media,
        "cmd": cmd,
    }
