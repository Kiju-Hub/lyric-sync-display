"""
사용자가 이미 가지고 있는 가사 텍스트(로컬 txt 파일 또는 직접 입력)에
실제 재생 위치를 기준으로 타이밍을 찍어 .lrc로 저장하는 도구.

이 프로그램은 인터넷에서 가사를 가져오거나 생성하지 않는다 - 사용자가 이미
가진 텍스트를 그대로 쓰고, "몇 초에 이 줄이 나오는지"만 GSMTC의 실제 재생
위치를 참고해 기록한다.

사용법:
    py -3 tools/sync_lyrics.py

Space 키: 지금 재생 위치를 현재 줄의 타임스탬프로 기록하고 다음 줄로 이동
Ctrl+C: 중단
"""

import asyncio
import sys
from pathlib import Path

import msvcrt

sys.path.append(str(Path(__file__).resolve().parent.parent))
from now_playing import get_now_playing  # noqa: E402


def load_lines() -> list[str]:
    choice = input("가사를 (1) 로컬 txt 파일에서 불러오기 (2) 직접 입력하기 - 번호 선택: ").strip()

    if choice == "1":
        path = input("txt 파일 경로: ").strip().strip('"')
        text = Path(path).read_text(encoding="utf-8")
        lines = [line.strip() for line in text.splitlines()]
    else:
        print("가사를 한 줄씩 입력하세요. 빈 줄에서 Enter만 누르면 끝.")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)

    return [line for line in lines if line]


def format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"[{minutes:02d}:{secs:05.2f}]"


async def main():
    lines = load_lines()
    if not lines:
        print("가사가 없어서 종료합니다.")
        return

    print(f"\n총 {len(lines)}줄 로드됨. 노래를 재생하고, 각 줄이 나오는 순간 Space를 누르세요.\n")

    entries = []
    index = 0
    while index < len(lines):
        print(f"[{index + 1}/{len(lines)}] {lines[index]}")

        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b" ":
                    now_playing = await get_now_playing()
                    position = now_playing["position"] if now_playing else 0.0
                    entries.append((position, lines[index]))
                    print(f"  -> {format_timestamp(position)} 기록됨\n")
                    index += 1
                    break
            await asyncio.sleep(0.05)

    lrc_text = "\n".join(f"{format_timestamp(t)}{text}" for t, text in entries) + "\n"

    print("\n--- 만들어진 LRC (타임스탬프만 확인용) ---")
    for t, _ in entries:
        print(" ", format_timestamp(t))

    out_path = input("\n저장할 파일 경로 (예: C:\\lyrics\\song.lrc): ").strip().strip('"')
    Path(out_path).write_text(lrc_text, encoding="utf-8")
    print(f"저장 완료: {out_path}")
    print("이제 tools/add_manual_lyrics.py로 이 파일을 등록하세요.")


if __name__ == "__main__":
    asyncio.run(main())
