"""제목 정규화 + LRCLIB 검색 + 로컬 캐시."""

import difflib
import hashlib
import json
import re
from pathlib import Path

import requests

from lrc_sync import parse_lrc

LRCLIB_BASE = "https://lrclib.net/api"
CACHE_DIR = Path(__file__).resolve().parent / "cache"

# 유튜브 등에서 제목에 흔히 붙는 잡음 패턴. 괄호/대괄호 안에 이 키워드가 있으면 통째로 제거
_NOISE_IN_BRACKETS = re.compile(
    r"[\(\[][^\)\]]*"
    r"(official\s*(video|audio|mv)|lyrics?|remaster(ed)?|live|m\/v|4k|hd)"
    r"[^\)\]]*[\)\]]",
    re.IGNORECASE,
)
_FEAT_SUFFIX = re.compile(r"\s*(feat\.?|ft\.?|featuring)\s+.+$", re.IGNORECASE)

# GSMTC가 주는 아티스트명이 국내 DB(LRCLIB 등)에는 공식 영문 표기로만 등록돼 있어서
# 검색이 실패하는 경우를 위한 별칭 테이블. 비슷한 경우를 만나면 여기에 추가하면 된다.
ARTIST_ALIASES = {
    "검정치마": "The Black Skirts",
}


def normalize_title(raw_title: str) -> str:
    """검색용으로 다듬은 제목. 화면 표시에는 원본 제목을 그대로 쓰고 이건 검색에만 사용."""
    title = _NOISE_IN_BRACKETS.sub("", raw_title)
    title = _FEAT_SUFFIX.sub("", title)
    return title.strip()


def _cache_path(artist: str, title: str) -> Path:
    key = hashlib.md5(f"{artist.lower()}|{title.lower()}".encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{key}.json"


def _load_cache(artist: str, title: str):
    path = _cache_path(artist, title)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_manual_lyrics(artist: str, title: str, lrc_text: str):
    """LRCLIB에 없는 곡을 위해 직접 구한/만든 LRC를 로컬 캐시에 등록한다 (tools/add_manual_lyrics.py에서 사용)."""
    _save_cache(artist, title, lrc_text)


def _save_cache(artist: str, title: str, synced_lyrics: str):
    CACHE_DIR.mkdir(exist_ok=True)
    path = _cache_path(artist, title)
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            {"title": title, "artist": artist, "syncedLyrics": synced_lyrics},
            f,
            ensure_ascii=False,
            indent=2,
        )


def _get_exact(track_name: str, artist_name: str, duration: int):
    resp = requests.get(
        f"{LRCLIB_BASE}/get",
        params={"track_name": track_name, "artist_name": artist_name, "duration": duration},
        timeout=5,
    )
    return resp.json() if resp.status_code == 200 else None


def _search_best(track_name: str, artist_name: str):
    """fuzzy 검색 후 제목 유사도가 가장 높은, syncedLyrics 있는 후보를 고른다."""
    resp = requests.get(
        f"{LRCLIB_BASE}/search",
        params={"track_name": track_name, "artist_name": artist_name},
        timeout=5,
    )
    if resp.status_code != 200:
        return None

    candidates = [c for c in resp.json() if c.get("syncedLyrics")]
    if not candidates:
        return None

    def score(candidate):
        return difflib.SequenceMatcher(
            None, track_name.lower(), candidate["trackName"].lower()
        ).ratio()

    return max(candidates, key=score)


def _try_search(title: str, artist: str, duration: float):
    result = _get_exact(title, artist, round(duration))
    if result is None or not result.get("syncedLyrics"):
        result = _search_best(title, artist)
    return result if result and result.get("syncedLyrics") else None


def find_synced_lyrics(raw_title: str, artist: str, duration: float):
    """
    (시간_초, 가사) 리스트를 반환한다. 못 찾으면 None.
    순서: 로컬 캐시 -> (원본 아티스트/제목, title을 "아티스트 - 제목"으로 쪼갠 버전,
    별칭 테이블로 바꾼 버전) 각각에 대해 정확 검색 -> fuzzy 검색.
    """
    cached = _load_cache(artist, raw_title)
    if cached:
        return parse_lrc(cached["syncedLyrics"])

    title = normalize_title(raw_title)
    candidates = [(title, artist)]

    # 유튜브류는 GSMTC의 artist가 채널명이고, 진짜 "아티스트 - 곡명"은 title 안에 들어있는 경우가 많다
    if " - " in title:
        maybe_artist, _, maybe_title = title.partition(" - ")
        candidates.append((maybe_title.strip(), maybe_artist.strip()))

    for search_title, search_artist in list(candidates):
        alias = ARTIST_ALIASES.get(search_artist)
        if alias:
            candidates.append((search_title, alias))

    for search_title, search_artist in candidates:
        result = _try_search(search_title, search_artist, duration)
        if result:
            _save_cache(artist, raw_title, result["syncedLyrics"])
            return parse_lrc(result["syncedLyrics"])

    return None
