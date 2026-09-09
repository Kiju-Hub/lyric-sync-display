"""
Step 6: 전체 통합

Windows에서 재생 중인 곡을 감지 -> LRCLIB에서 동기화 가사 검색
-> 현재 재생 위치에 맞는 줄 계산 -> ESP32로 시리얼 전송.
"""

import asyncio
import time

import config
from lrc_sync import build_phrase_timeline, find_current_index
from lyrics import find_synced_lyrics
from now_playing import get_now_playing
from serial_comm import LyricsSerial


def song_id(artist: str, title: str) -> str:
    return f"{artist.strip().lower()}|{title.strip().lower()}"


class SyncState:
    """monotonic 시계로 재생 위치를 보정해서 GSMTC의 낮은 갱신 빈도를 완화한다."""

    def __init__(self):
        self.anchor_position = 0.0
        self.anchor_time = time.monotonic()
        self.is_playing = False
        self.last_raw_position = None

    def update(self, raw_position: float, is_playing: bool):
        # GSMTC는 몇 초에 한 번씩만 값을 갱신하고, 그 사이에는 같은 값을 반복해서 돌려준다.
        # "지난번에 받은 raw 값과 실제로 다른가"로만 진짜 갱신(또는 탐색/재생상태 변화)을 판단한다.
        # (우리 자신의 추정치와 비교하면 안 됨 - 추정치는 항상 앞서 나가있어서 매번 다르게 나옴)
        changed = raw_position != self.last_raw_position or is_playing != self.is_playing

        if changed:
            self.anchor_position = raw_position
            self.anchor_time = time.monotonic()

        self.last_raw_position = raw_position
        self.is_playing = is_playing

    def estimate(self) -> float:
        if not self.is_playing:
            return self.anchor_position
        elapsed = time.monotonic() - self.anchor_time
        return self.anchor_position + elapsed


async def main():
    esp32 = LyricsSerial(config.SERIAL_PORT, config.SERIAL_BAUD)
    sync_state = SyncState()

    current_song_id = None
    timeline = None            # (시간, 구절) 목록 전체를 곡이 바뀔 때 한 번만 미리 계산해둠
    timeline_index = -1        # 지금까지 실제로 전송한 구절의 인덱스 (이걸 한 칸씩만 전진시킴)
    last_sent_time = 0.0        # 마지막으로 화면을 바꾼 monotonic 시각 (최소 유지시간 계산용)

    print("실행 중... 노래를 재생하면 자동으로 가사를 찾아 ESP32로 보냅니다. (Ctrl+C로 종료)")

    while True:
        now_playing = await get_now_playing()

        if now_playing is not None:
            sid = song_id(now_playing["artist"], now_playing["title"])

            if sid != current_song_id:
                current_song_id = sid
                timeline_index = -1
                last_sent_time = 0.0  # 새 곡의 첫 구절은 최소 유지시간 제한 없이 바로 표시
                print(f"곡 변경 감지: {now_playing['artist']} - {now_playing['title']}")

                # 간주(첫 가사 나오기 전)에는 곡 제목을 큰 글씨로 띄워둠. 검색이 끝나서
                # 첫 구절이 전송되는 순간 자동으로 덮어써지므로 별도로 지울 필요는 없음.
                esp32.send_title(now_playing["title"])

                lines = find_synced_lyrics(
                    now_playing["title"], now_playing["artist"], now_playing["duration"]
                )
                if lines is None:
                    print("  -> 동기화 가사를 찾지 못했습니다.")
                    esp32.send_line(config.NO_LYRICS_MESSAGE)
                    timeline = None
                else:
                    timeline = build_phrase_timeline(lines, config.MIN_DISPLAY_SEC)
                    print(f"  -> 가사 {len(lines)}줄 -> 구절 {len(timeline)}개로 준비됨")

            sync_state.update(now_playing["position"], now_playing["status"] == "PLAYING")

            if timeline is not None:
                position = sync_state.estimate() + config.LYRIC_OFFSET_SEC
                target_index = find_current_index(timeline, position)

                elapsed_since_last = time.monotonic() - last_sent_time
                # target_index가 훨씬 앞서 있어도(빠른 구간 등) 한 번에 한 칸씩만 전진한다.
                # 이렇게 하면 화면이 노래보다 잠깐 밀릴 순 있어도 구절을 하나도 건너뛰지 않는다.
                if target_index > timeline_index and elapsed_since_last >= config.MIN_DISPLAY_SEC:
                    timeline_index += 1
                    phrase = timeline[timeline_index][1]
                    if phrase:
                        # 빈 구절(간주 등)이면 화면은 이전 가사 그대로 두고 인덱스만 넘긴다.
                        # last_sent_time을 갱신하지 않으므로, 다음 실제 가사는 최소 유지시간 대기 없이 바로 표시된다.
                        esp32.send_line(phrase)
                        last_sent_time = time.monotonic()
                        print(f"[{position:.1f}s] {phrase}")

        await asyncio.sleep(config.POLL_INTERVAL_SEC)


if __name__ == "__main__":
    asyncio.run(main())
