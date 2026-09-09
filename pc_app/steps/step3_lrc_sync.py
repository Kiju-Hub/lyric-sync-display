"""
Step 3: LRC 동기화 엔진 테스트

1) 고정된 샘플 LRC로 파서 + 현재 줄 계산 로직이 맞는지 확인
2) 실제로 지금 재생 중인 곡(GSMTC)의 실시간 위치 + 방금 검색한 LRC로
   현재 가사 줄이 잘 따라오는지 실시간으로 확인

성공 기준: 1)의 결과가 기대값과 일치하고, 2)에서 노래를 재생하면
콘솔에 찍히는 가사 줄이 실제 노래 진행과 맞아떨어지면 성공.
"""

import asyncio
import sys
from pathlib import Path

import requests
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lrc_sync import parse_lrc, get_current_line  # noqa: E402

LRCLIB_BASE = "https://lrclib.net/api"

SAMPLE_LRC = """\
[00:12.30]Hello
[00:16.52]This is a song
[00:20.21]Example lyrics
"""


def test_static():
    print("=== 1) 고정 샘플 테스트 ===")
    lines = parse_lrc(SAMPLE_LRC)
    cases = [
        (0.0, None),
        (10.0, None),
        (12.30, "Hello"),
        (18.4, "This is a song"),
        (25.0, "Example lyrics"),
    ]
    for position, expected in cases:
        actual = get_current_line(lines, position)
        ok = "OK" if actual == expected else "FAIL"
        print(f"[{ok}] position={position} -> {actual!r} (기대값: {expected!r})")


async def get_now_playing():
    manager = await MediaManager.request_async()
    session = manager.get_current_session()
    if session is None:
        return None
    info = await session.try_get_media_properties_async()
    timeline = session.get_timeline_properties()
    return {
        "title": info.title,
        "artist": info.artist,
        "position": timeline.position.total_seconds(),
    }


async def test_live():
    print("\n=== 2) 실시간 테스트 (지금 재생 중인 곡 기준) ===")
    now_playing = await get_now_playing()
    if now_playing is None:
        print("재생 중인 곡이 없어서 실시간 테스트를 건너뜁니다.")
        return

    print(f"곡 감지: {now_playing['artist']} - {now_playing['title']}")
    resp = requests.get(
        f"{LRCLIB_BASE}/get",
        params={"track_name": now_playing["title"], "artist_name": now_playing["artist"]},
        timeout=5,
    )
    if resp.status_code != 200 or not resp.json().get("syncedLyrics"):
        print("이 곡은 동기화 가사를 찾지 못해 실시간 테스트를 건너뜁니다.")
        return

    lines = parse_lrc(resp.json()["syncedLyrics"])
    print("가사를 찾았습니다. 노래를 재생 상태로 두면 아래에 현재 줄이 계속 갱신됩니다 (Ctrl+C로 종료).")

    last_shown = object()
    while True:
        now_playing = await get_now_playing()
        if now_playing is not None:
            current = get_current_line(lines, now_playing["position"])
            if current != last_shown:
                print(f"[{now_playing['position']:.1f}s] {current}")
                last_shown = current
        await asyncio.sleep(1)


async def main():
    test_static()
    await test_live()


if __name__ == "__main__":
    asyncio.run(main())
