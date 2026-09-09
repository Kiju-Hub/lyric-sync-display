"""
Step 4: PC -> USB Serial -> ESP32 테스트

ESP32가 "LYRIC|텍스트" 형식의 줄을 받아 OLED에 표시하는지 확인한다.
main.cpp를 먼저 업로드해둔 상태여야 한다.

성공 기준: 이 스크립트를 실행하면 몇 초 간격으로 다른 문장이 OLED에 바뀌어 나타나야 한다.
"""

import time

import serial

PORT = "COM3"
BAUD = 115200

TEST_LINES = [
    "Hello ESP32",
    "한글도 잘 나오나요",
    "wave to earth - love.",
    "사람 사이 사람",
]


def main():
    with serial.Serial(PORT, BAUD, timeout=2) as ser:
        time.sleep(2)  # ESP32가 시리얼 연결 시 자동 리셋되므로 부팅 완료까지 대기
        ser.reset_input_buffer()  # 리셋 직후 쏟아지는 부팅 로그를 버림 (readline이 이걸 읽지 않도록)

        for text in TEST_LINES:
            message = f"LYRIC|{text}\n"
            ser.write(message.encode("utf-8"))
            print(f"보냄: {text}")

            reply = ser.readline().decode("utf-8", errors="replace").strip()
            print(f"ESP32 응답: {reply}")

            time.sleep(3)  # 화면에서 눈으로 확인할 시간


if __name__ == "__main__":
    main()
