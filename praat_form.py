import re
from typing import Optional


_FIELD_TYPES = {
    "word", "sentence", "text", "real", "positive", "integer", "natural",
    "boolean", "choice", "optionmenu", "infile", "outfile", "folder",
    "realvector", "positivevector", "integervector", "naturalvector",
}

_FORM_RE = re.compile(r"^\s*form\b\s*:?\s*(.*?)\s*$", re.IGNORECASE)
_ENDFORM_RE = re.compile(r"^\s*endform\b", re.IGNORECASE)
_LINE_RE = re.compile(r"^(\w+)\s*:?\s*(.*)$")
_QUOTE_CHARS = "\"“”"


def _strip_quotes(s: str) -> str:
    s = s.strip().rstrip(",").strip()
    if len(s) >= 2 and s[0] in _QUOTE_CHARS and s[-1] in _QUOTE_CHARS:
        s = s[1:-1]
    return s


def _to_variable_name(label: str) -> str:
    """ Praat 변환 규칙: 끝의 (단위) 제거 -> 공백을 밑줄로 -> 첫 글자만 소문자 """
    name = re.sub(r"\s*\([^)]*\)\s*$", "", label).strip()
    name = re.sub(r"\s+", "_", name)
    if name:
        name = name[0].lower() + name[1:]
    return name


def parse_form(source: str) -> Optional[dict]:
    """
    스크립트의 form~endform 블록을 파싱.
    구문법(공백 구분, 따옴표 없음)과 신문법(콜론 + 따옴표) 둘 다 지원.
    반환: {"title": str, "fields": [...]} 또는 form이 없으면 None.
    각 field: {keyword, label, variable, default, arg_position, is_input, options?}
    comment 필드는 {"keyword": "comment", "text": ..., "is_input": False}
    """
    lines = source.splitlines()

    start = None
    for i, line in enumerate(lines):
        if _FORM_RE.match(line):
            start = i
            break
    if start is None:
        return None

    title = _strip_quotes(_FORM_RE.match(lines[start]).group(1))
    fields: list[dict] = []
    last_choice: Optional[dict] = None
    arg_position = 0

    for line in lines[start + 1:]:
        if _ENDFORM_RE.match(line):
            break
        stripped = line.strip()
        if not stripped:
            continue

        m = _LINE_RE.match(stripped)
        if not m:
            continue
        keyword, rest = m.group(1), m.group(2)
        kw_lower = keyword.lower()

        if kw_lower == "option":
            if last_choice is not None:
                last_choice["options"].append(_strip_quotes(rest))
            continue

        if kw_lower == "comment":
            fields.append({
                "keyword": "comment",
                "text": _strip_quotes(rest),
                "is_input": False,
            })
            last_choice = None
            continue

        if kw_lower not in _FIELD_TYPES:
            continue

        if any(c in rest for c in _QUOTE_CHARS):
            parts = [_strip_quotes(p) for p in re.split(r"\s*,\s*", rest)]
        else:
            parts = rest.split(None, 1)

        if not parts:
            continue

        raw_name = parts[0]
        default = parts[1] if len(parts) > 1 else ""

        var_name = _to_variable_name(raw_name) if " " in raw_name else raw_name

        arg_position += 1
        field = {
            "keyword": kw_lower,
            "label": raw_name,
            "variable": var_name,
            "default": default,
            "arg_position": arg_position,
            "is_input": True,
        }
        if kw_lower in ("choice", "optionmenu"):
            field["options"] = []
            last_choice = field
        else:
            last_choice = None
        fields.append(field)

    return {"title": title, "fields": fields}
