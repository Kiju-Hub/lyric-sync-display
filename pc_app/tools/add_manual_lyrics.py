"""
LRCLIB에 없는 곡을 위해 직접 구한/만든 LRC 파일을 로컬 캐시에 등록하는 도구.

주의: 아티스트명/제목은 실제 재생 시 GSMTC가 인식하는 것과 정확히 똑같아야
main.py가 캐시를 찾아낸다. 먼저 steps/step1_now_playing.py로 그 곡을 재생하면서
콘솔에 찍히는 artist/title 문자열을 그대로 복사해서 쓰는 걸 추천한다.

사용법:
    py -3 tools/add_manual_lyrics.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lyrics import save_manual_lyrics  # noqa: E402


def main():
    print("=== LRCLIB에 없는 곡을 위한 수동 가사 등록 ===")
    artist = input("아티스트명 (GSMTC에 뜨는 것과 정확히 동일하게): ").strip()
    title = input("곡 제목 (GSMTC에 뜨는 것과 정확히 동일하게): ").strip()
    lrc_path = input("LRC 파일 경로 (예: C:\\lyrics\\song.lrc): ").strip().strip('"')

    path = Path(lrc_path)
    if not path.exists():
        print(f"파일을 찾을 수 없습니다: {path}")
        return

    lrc_text = path.read_text(encoding="utf-8")
    save_manual_lyrics(artist, title, lrc_text)
    print(f"등록 완료: {artist} - {title}")
    print("이제 이 곡을 재생하면 main.py가 자동으로 캐시에서 찾아 표시합니다.")


if __name__ == "__main__":
    main()
