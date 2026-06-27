from pathlib import Path


def _decode_utf16_bytes(data: bytes) -> str:
    """
    UTF-16 고정 디코딩.
    - BOM 있으면 utf-16로 처리
    - BOM 없으면 Windows 가정으로 UTF-16-LE 처리
    """
    if not data:
        return ""
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    return data.decode("utf-16-le", errors="replace")

def _read_script_text(path: Path) -> str:
    """
    스크립트는 UTF-8/UTF-16 섞일 수 있으니:
    - BOM 있으면 utf-16/utf-8-sig 처리
    - 아니면 utf-8 우선, 그 다음 utf-16-le
    """
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace")

    # 대부분 praat 스크립트는 utf-8/plain일 가능성이 높음
    text = data.decode("utf-8", errors="replace")
    return text

def discover_scripts(path: Path) -> dict[str, Path]:
    scripts: dict[str, Path] = {}
    for p in path.glob("*.praat"):
        if p.is_file():
            scripts[p.stem] = p.resolve()
    return scripts
