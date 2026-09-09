"""
노래를 들으면서 직접 타이밍을 찍어 LRC 파일을 만드는 도구.
(LRCLIB에 없는 곡의 가사를 직접 등록하기 위한 용도)

사용법:
    py -3 tools/make_lrc.py

1. 노래를 재생 0초 지점에서 같이 시작한다는 느낌으로, 이 스크립트도 같이 실행해서 Enter를 누른다 (시작점).
2. 이후 가사 한 줄이 시작되는 "그 순간"마다 Enter를 눌러 시간을 찍고,
   이어서 그 줄의 가사 텍스트를 입력한다 (텍스트 입력하는 동안 노래는 계속 흘러가도 됨,
   타임스탬프는 Enter를 누른 시점 기준이라 괜찮음).
3. 끝나면 빈 줄에서 Enter만 눌러 종료하고, 저장할 파일 경로를 입력한다.
"""

import time
from pathlib import Path


def format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"[{minutes:02d}:{secs:05.2f}]"


def main():
    print("=== LRC 직접 만들기 ===")
    input("노래를 0초에 재생하고, 재생 시작하는 순간 Enter를 누르세요...")
    start_time = time.monotonic()
    print("시작! 이제 가사 줄이 나올 때마다 Enter를 누르고 텍스트를 입력하세요. (끝내려면 빈 줄에서 Enter)")

    entries = []
    while True:
        input()  # 이 Enter를 누른 순간이 이 줄의 타임스탬프
        timestamp = time.monotonic() - start_time
        text = input(f"{format_timestamp(timestamp)} 가사: ").strip()
        if text == "":
            break
        entries.append((timestamp, text))

    if not entries:
        print("입력된 줄이 없어서 저장하지 않습니다.")
        return

    lrc_lines = [f"{format_timestamp(t)}{text}" for t, text in entries]
    lrc_text = "\n".join(lrc_lines) + "\n"

    print("\n--- 만들어진 LRC ---")
    print(lrc_text)

    out_path = input("저장할 파일 경로 (예: C:\\lyrics\\song.lrc): ").strip().strip('"')
    Path(out_path).write_text(lrc_text, encoding="utf-8")
    print(f"저장 완료: {out_path}")
    print("이제 tools/add_manual_lyrics.py로 이 파일을 등록하세요.")


if __name__ == "__main__":
    main()
