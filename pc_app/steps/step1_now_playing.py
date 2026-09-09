"""
Step 1: Windows Now Playing (GSMTC) 테스트

지금 PC에서 재생 중인 미디어(Spotify, 유튜브 등)의
title / artist / position / status를 1초마다 출력한다.

성공 기준: Spotify나 유튜브에서 음악을 재생한 상태로 이 스크립트를 실행했을 때
콘솔에 올바른 제목/아티스트/재생위치가 계속 갱신되며 찍히면 성공.
"""

import asyncio

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)


async def get_now_playing():
    manager = await MediaManager.request_async()
    session = manager.get_current_session()

    if session is None:
        return None

    info = await session.try_get_media_properties_async()
    timeline = session.get_timeline_properties()
    playback_info = session.get_playback_info()

    return {
        "title": info.title,
        "artist": info.artist,
        "position": timeline.position.total_seconds(),
        "duration": timeline.end_time.total_seconds(),
        "status": playback_info.playback_status.name,  # PLAYING / PAUSED / STOPPED 등
    }


async def main():
    while True:
        now_playing = await get_now_playing()

        if now_playing is None:
            print("재생 중인 미디어 세션이 없습니다.")
        else:
            print(
                f"[{now_playing['status']}] "
                f"{now_playing['artist']} - {now_playing['title']} "
                f"({now_playing['position']:.1f}s / {now_playing['duration']:.1f}s)"
            )

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
