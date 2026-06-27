import os, re

from dotenv import load_dotenv

from configuration import AppConfig
from pathlib import Path


ENV_KEY = [
    "MCP_ROOT_DIR",
    "PRAAT_EXE_DIR",
    "SCRIPT_DIR",
    "RESULT_DIR",
]

_BRACED = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

def require_env(key: str) -> str:
    v = os.getenv(key)
    if v is None or not v.strip():
        raise KeyError(f"Missing env: {key}")
    return v.strip()

def expand_braced_vars(value: str, env: dict[str, str], max_passes: int = 20) -> str:
    """ .env 에서 {KEY} 형태 확장 지원 """
    cur = value
    for _ in range(max_passes):
        def repl(m: re.Match) -> str:
            k = m.group(1)
            if k not in env or not env[k].strip():
                raise KeyError(f"Undefined placeholder {{{k}}} in {value!r}")
            return env[k]
        nxt = _BRACED.sub(repl, cur)
        if nxt == cur:
            return cur
        cur = nxt
    raise ValueError(f"Too many expansions (cycle?) for {value!r}")

def to_path(raw: str) -> Path:
    """
    1) {KEY} 확장
    2) %VAR% / $VAR 확장
    3) ~ 확장
    4) Path.resolve()
    """
    env = {k: v for k, v in os.environ.items() if isinstance(v, str)}
    s = expand_braced_vars(raw, env)
    s = os.path.expandvars(os.path.expanduser(s))
    return Path(s).resolve()

def boot_up(logger) -> AppConfig:
    load_dotenv()

    for k in ENV_KEY:
        require_env(k)

    cfg = AppConfig(
        root_dir=to_path(require_env("MCP_ROOT_DIR")),
        praat_exe_dir=to_path(require_env("PRAAT_EXE_DIR")),
        script_dir=to_path(require_env("SCRIPT_DIR")),
        result_dir=to_path(require_env("RESULT_DIR")),
    )

    cfg.result_dir.mkdir(parents=True, exist_ok=True)

    if not cfg.praat_exe_path.exists():
        raise FileNotFoundError(f"Praat.exe not found: {cfg.praat_exe_path}")
    if not cfg.script_dir.exists():
        raise FileNotFoundError(f"SCRIPT_DIR not found: {cfg.script_dir}")

    logger.info("praat_exe_dir  = %s", cfg.praat_exe_dir)
    logger.info("praat_exe_path = %s", cfg.praat_exe_path)
    logger.info("script_dir     = %s", cfg.script_dir)
    logger.info("result_dir     = %s", cfg.result_dir)

    return cfg
