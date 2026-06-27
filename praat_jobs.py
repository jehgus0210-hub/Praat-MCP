import subprocess, os, uuid, time, threading
from typing import Optional
from pathlib import Path

from encoding import _decode_utf16_bytes, _read_script_text, discover_scripts
from praat_analysis import find_blocking_commands, snapshot_files, collect_new_media


_lock = threading.Lock()
_jobs: dict[str, dict] = {}


def start(
    logger,
    cfg,
    script_id: str,
    audio_path: str,
    args: Optional[list[str]] = None,
    timeout_sec: Optional[int] = None,
) -> dict:
    """
    오래 걸리는 Praat 스크립트를 백그라운드(Popen)로 시작하고 즉시 job_id를 반환.
    상태/결과는 status()로 폴링해서 가져온다.
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

    out_file = (cfg.result_dir / f"{job_id}.txt").resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    stdout_file = cfg.result_dir / f"{job_id}.stdout.log"
    stderr_file = cfg.result_dir / f"{job_id}.stderr.log"

    audio_p = Path(os.path.expandvars(os.path.expanduser(audio_path))).resolve()

    cmd = [
        str(cfg.praat_exe_path),
        "--run",
        "--no-pref-files",
        str(script_path),
        str(audio_p),
        str(out_file),
        *args,
    ]

    logger.info("START job=%s script=%s audio=%s out=%s", job_id, script_id, audio_p, out_file)

    before = snapshot_files(cfg.result_dir)

    stdout_fh = open(stdout_file, "wb")
    stderr_fh = open(stderr_file, "wb")
    proc = subprocess.Popen(cmd, stdout=stdout_fh, stderr=stderr_fh, shell=False)

    with _lock:
        _jobs[job_id] = {
            "proc": proc,
            "stdout_fh": stdout_fh,
            "stderr_fh": stderr_fh,
            "stdout_file": stdout_file,
            "stderr_file": stderr_file,
            "out_file": out_file,
            "script_id": script_id,
            "started_at": time.time(),
            "timeout_sec": timeout_sec,
            "before_snapshot": before,
            "cmd": cmd,
            "handles_closed": False,
        }

    return {"job_id": job_id, "status": "running", "cmd": cmd}


def status(cfg, job_id: str, wait_sec: float = 0) -> dict:
    """
    wait_sec > 0이면, 작업이 끝나거나 wait_sec가 지날 때까지 서버가 내부적으로
    기다렸다가 결과를 반환한다. 매번 승인이 필요한 폴링 호출 횟수를 줄이는 용도.
    """
    with _lock:
        job = _jobs.get(job_id)
    if job is None:
        raise ValueError(f"Unknown job_id: {job_id}")

    proc: subprocess.Popen = job["proc"]
    deadline = time.time() + max(0.0, wait_sec)

    while True:
        elapsed = time.time() - job["started_at"]
        ret = proc.poll()
        timed_out = False
        if ret is None and job["timeout_sec"] is not None and elapsed > job["timeout_sec"]:
            proc.kill()
            ret = proc.wait()
            timed_out = True

        if ret is not None or time.time() >= deadline:
            break
        time.sleep(min(2.0, deadline - time.time()))

    if ret is None:
        return {"job_id": job_id, "status": "running", "elapsed_sec": round(elapsed, 1)}

    with _lock:
        if not job["handles_closed"]:
            job["stdout_fh"].close()
            job["stderr_fh"].close()
            job["handles_closed"] = True

    stdout_file: Path = job["stdout_file"]
    stderr_file: Path = job["stderr_file"]
    stdout = _decode_utf16_bytes(stdout_file.read_bytes()) if stdout_file.exists() else ""
    stderr = _decode_utf16_bytes(stderr_file.read_bytes()) if stderr_file.exists() else ""

    out_file: Path = job["out_file"]
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

    media = collect_new_media(job["before_snapshot"], cfg.result_dir, exclude={out_file})

    if timed_out:
        job_status = "timeout"
    elif ret == 0:
        job_status = "done"
    else:
        job_status = "error"

    return {
        "job_id": job_id,
        "status": job_status,
        "elapsed_sec": round(elapsed, 1),
        "exit_code": ret,
        "stdout": stdout,
        "stderr": stderr,
        "output": output_meta,
        "result_text": result_text,
        "media": media,
        "cmd": job["cmd"],
    }
