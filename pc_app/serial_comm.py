"""ESP32로 LYRIC| 프로토콜 전송."""

import time

import serial


class LyricsSerial:
    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self._ser = None

    def _connect(self):
        self._ser = serial.Serial(self.port, self.baud, timeout=2)
        time.sleep(2)  # ESP32가 포트 오픈 시 자동 리셋되므로 부팅 완료까지 대기
        self._ser.reset_input_buffer()  # 부팅 로그 버림

    def send_line(self, text: str, prefix: str = "LYRIC"):
        """연결이 끊겨 있으면 재연결을 시도하고, 실패하면 조용히 넘어간다 (음악 재생엔 지장 없어야 함)."""
        try:
            if self._ser is None:
                self._connect()
            self._ser.write(f"{prefix}|{text}\n".encode("utf-8"))
        except serial.SerialException:
            print(f"[serial] ESP32 연결 끊김 (port={self.port}), 다음 전송 때 재시도합니다.")
            self._ser = None

    def send_title(self, text: str):
        """간주 중 곡 제목을 큰 글씨로 표시 (ESP32의 TITLE| 프로토콜)."""
        self.send_line(text, prefix="TITLE")
