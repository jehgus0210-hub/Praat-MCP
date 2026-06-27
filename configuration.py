from pathlib import Path

def resolve_praat_exe(praat_exe_dir_or_path: Path) -> Path:
    """
    PRAAT_EXE_DIR를 '폴더'로 받되,
    실수로 exe 풀경로를 넣어도 자동으로 처리
    """
    p = praat_exe_dir_or_path
    if p.suffix.lower() == ".exe" and p.name.lower() == "praat.exe":
        return p.resolve()
    return (p / "Praat.exe").resolve()

class AppConfig:
    def __init__(self, root_dir: Path, praat_exe_dir: Path, script_dir: Path, result_dir: Path):
        self._root_dir = root_dir
        self._praat_exe_dir = praat_exe_dir
        self._praat_exe_path = resolve_praat_exe(praat_exe_dir)
        self._script_dir = script_dir
        self._result_dir = result_dir

    @property
    def root_dir(self) -> Path: return self._root_dir

    @property
    def praat_exe_dir(self) -> Path: return self._praat_exe_dir

    @property
    def praat_exe_path(self) -> Path: return self._praat_exe_path

    @property
    def script_dir(self) -> Path: return self._script_dir

    @property
    def result_dir(self) -> Path: return self._result_dir
