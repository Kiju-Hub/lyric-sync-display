"""
LRC 파싱 + 현재 재생 위치에 맞는 가사 한 줄 찾기.
"""

import re

_LINE_PATTERN = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")


def parse_lrc(lrc_text: str) -> list[tuple[float, str]]:
    """
    "[00:12.30]Hello" 형태의 LRC 텍스트를 (시간_초, 가사) 리스트로 변환한다.
    [ar:...], [ti:...] 같은 메타데이터 태그 줄은 자동으로 무시된다 (분:초 형식이 아니므로 매치 안 됨).
    """
    lines = []
    for raw_line in lrc_text.splitlines():
        match = _LINE_PATTERN.match(raw_line.strip())
        if not match:
            continue
        minutes, seconds, text = match.groups()
        time_sec = int(minutes) * 60 + float(seconds)
        lines.append((time_sec, text.strip()))

    lines.sort(key=lambda pair: pair[0])
    return lines


def get_current_line(lines: list[tuple[float, str]], position: float) -> str | None:
    """
    lines[i].time <= position < lines[i+1].time 인 lines[i]의 가사를 반환한다.
    position이 첫 줄보다 앞이면 None을 반환한다.
    """
    current = None
    for time_sec, text in lines:
        if time_sec <= position:
            current = text
        else:
            break
    return current


DEFAULT_LINE_WINDOW_SEC = 5.0  # 마지막 줄처럼 다음 줄이 없을 때 이 구간이 유지된다고 가정


def split_into_phrases(text: str, window_duration: float, min_phrase_sec: float) -> list[str]:
    """
    긴 가사 한 줄을 여러 구절로 쪼갠다 (한 줄의 시간 구간 안에서 순차적으로 보여주기 위함).
    쉼표가 있으면 그 기준으로, 없고 단어 수가 많으면 절반으로 나눈다.

    단, 나눴을 때 구절 하나당 배정되는 시간이 min_phrase_sec보다 짧으면 나누지 않는다.
    (안 그러면 뒤쪽 구절이 "최소 유지시간"에 걸려 노래가 거의 끝나갈 때쯤 늦게 나타나게 됨)
    """
    candidates = None

    if "," in text:
        candidates = [p.strip() for p in text.split(",") if p.strip()]

    if not candidates:
        words = text.split()
        if len(words) > 4:
            mid = len(words) // 2
            candidates = [" ".join(words[:mid]), " ".join(words[mid:])]

    if not candidates:
        return [text]

    if window_duration / len(candidates) < min_phrase_sec:
        return [text]

    return candidates


def build_phrase_timeline(
    lines: list[tuple[float, str]], min_phrase_sec: float
) -> list[tuple[float, str]]:
    """
    LRC 줄 목록을 구절 단위로 미리 다 펼쳐서 (시간, 구절) 목록으로 만든다.
    한 줄이 여러 구절로 나뉘면, 그 줄의 시간 구간을 구절 수만큼 균등하게 쪼갠 시작 시간을 배정한다.
    한 번만 계산해두고 재생 내내 순서대로 소비하기 위한 것 (매 폴링마다 다시 계산할 필요 없음).
    """
    timeline = []
    for i, (start_time, text) in enumerate(lines):
        end_time = lines[i + 1][0] if i + 1 < len(lines) else start_time + DEFAULT_LINE_WINDOW_SEC
        phrases = split_into_phrases(text, end_time - start_time, min_phrase_sec)
        span = (end_time - start_time) / len(phrases)
        for j, phrase in enumerate(phrases):
            timeline.append((start_time + j * span, phrase))
    return timeline


def find_current_index(timeline: list[tuple[float, str]], position: float) -> int:
    """timeline[i].time <= position인 가장 마지막 i를 반환한다. 없으면 -1."""
    current = -1
    for i, (time_sec, _text) in enumerate(timeline):
        if time_sec <= position:
            current = i
        else:
            break
    return current
