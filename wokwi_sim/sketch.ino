#include <U8g2lib.h>
#include <Wire.h>

// Wokwi 시뮬레이션용: 실제 하드웨어는 SH1106이지만 Wokwi 부품 라이브러리에
// SSD1306만 있어서 시뮬레이션은 SSD1306 드라이버로 대체 (배선/레이아웃 테스트 목적)
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

void setup() {
  Serial.begin(115200);

  u8g2.begin();
  u8g2.setFont(u8g2_font_ncenB10_tr);

  u8g2.clearBuffer();
  
  u8g2.drawStr(20, 35, "Hello World");
  u8g2.sendBuffer();

  Serial.println("OLED 초기화 완료, Hello World 출력됨");
}

void loop() {
}
