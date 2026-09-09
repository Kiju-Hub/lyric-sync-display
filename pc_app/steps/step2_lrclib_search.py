"""
Step 2: LRCLIB 동기화 가사 검색 테스트

Step 1에서 감지한 곡 정보(제목/아티스트/길이)로 LRCLIB API에 검색 요청을 보내
syncedLyrics(LRC 형식 문자열)를 받아오는지 확인한다.

성공 기준: 아래 SONG 정보로 실행했을 때 syncedLyrics 텍스트가 콘솔에 출력되면 성공.
"""

import requests

LRCLIB_BASE = "https://lrclib.net/api"

# Step 1에서 실제로 감지된 곡으로 테스트
SONG = {
    "track_name": "love.",
    "artist_name": "wave to earth",
    "duration": 308,  # 초 단위, 반올림
}


def get_exact(track_name: str, artist_name: str, duration: int):
    """정확 검색: track_name + artist_name + duration이 다 맞아야 함"""
    resp = requests.get(
        f"{LRCLIB_BASE}/get",
        params={
            "track_name": track_name,
            "artist_name": artist_name,
            "duration": duration,
        },
        timeout=5,
    )
    if resp.status_code == 200:
        return resp.json()
    return None


def search_fuzzy(track_name: str, artist_name: str):
    """fuzzy 검색: 후보 목록을 반환"""
    resp = requests.get(
        f"{LRCLIB_BASE}/search",
        params={"track_name": track_name, "artist_name": artist_name},
        timeout=5,
    )
    if resp.status_code == 200:
        return resp.json()
    return []


def main():
    print(f"정확 검색 시도: {SONG['artist_name']} - {SONG['track_name']} ({SONG['duration']}s)")
    result = get_exact(**SONG)

    if result is None:
        print("정확 검색 실패, fuzzy 검색으로 재시도합니다.")
        candidates = search_fuzzy(SONG["track_name"], SONG["artist_name"])
        print(f"fuzzy 검색 결과 {len(candidates)}건")
        result = next((c for c in candidates if c.get("syncedLyrics")), None)

    if result is None:
        print("동기화 가사를 찾지 못했습니다.")
        return

    synced = result.get("syncedLyrics")
    if synced:
        print("=== syncedLyrics 찾음 ===")
        print(synced)
    else:
        print("이 곡은 검색은 됐지만 syncedLyrics가 없습니다.")
        print("plainLyrics:", result.get("plainLyrics"))


if __name__ == "__main__":
    main()
