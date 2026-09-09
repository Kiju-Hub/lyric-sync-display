#include <Arduino.h>   // ESP32 아두이노 프레임워크 기본 함수(Serial, pinMode 등) 사용을 위해 필요
#include <U8g2lib.h>    // OLED 그래픽/텍스트를 그리기 위한 U8g2 라이브러리
#include <Wire.h>       // I2C 통신(U8g2가 내부적으로 사용)을 위해 필요
#include <math.h>       // 파도 애니메이션의 sin() 계산용

// SH1106 128x64 I2C, 하드웨어 I2C 사용, 별도 리셋 핀 없음(U8X8_PIN_NONE)
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);

const int LYRIC_LINE_HEIGHT = 13;   // 가사용 작은 폰트(gulim11) 줄 높이
const int LYRIC_MAX_LINES = 3;
const int TITLE_LINE_HEIGHT = 16;   // 곡 제목용 큰 폰트(gulim16) 줄 높이
const int TITLE_MAX_LINES = 2;
const int MAX_LINES_CAP = 3;        // 배열 크기용 (둘 중 큰 값)

bool isTitleMode = false;    // true면 간주 중 곡 제목을, false면 가사를 표시

const int BAR_COUNT = 16;                          // 스펙트럼 막대 개수
const int BAR_WIDTH = 128 / BAR_COUNT;              // 막대 하나의 폭(px)
const int BAR_AREA_TOP = 40;                        // 막대 영역 시작 y (여기부터 화면 맨 아래까지가 막대 영역)
const int BAR_MIN_HEIGHT = 2;
const int BAR_MAX_HEIGHT = 64 - BAR_AREA_TOP;       // 막대가 올라갈 수 있는 최대 높이
int barHeights[BAR_COUNT];

const int TEXT_AREA_HEIGHT = BAR_AREA_TOP;          // 막대 영역 위쪽, 텍스트가 들어갈 공간

const int SNOW_COUNT = 20;    // 눈처럼 흩날리는 점 개수
int snowX[SNOW_COUNT];
int snowY[SNOW_COUNT];

// 배경 스타일 전환 버튼 (GPIO4를 GND에 연결하는 버튼. 내부 풀업 사용이라 저항 불필요)
const int BUTTON_PIN = 4;
const int BG_MODE_BARS = 0;
const int BG_MODE_WAVE = 1;
const int BG_MODE_VINYL = 2;
const int NUM_BACKGROUND_MODES = 3;  // 막대 -> 파도 -> 턴테이블 순으로 순회
int backgroundMode = BG_MODE_BARS;
int buttonRawState = HIGH;
int buttonStableState = HIGH;
unsigned long buttonLastEdgeMs = 0;
const unsigned long BUTTON_DEBOUNCE_MS = 40;

// 파도 애니메이션 상태: wavePhase가 파도가 옆으로 흐르는 속도, ampPhase가 밀려왔다 쓸려가는 진폭 변화 속도
float wavePhase = 0;
float waveAmpPhase = 0;

String currentText = "";      // 지금 화면에 표시할 가사. 매 프레임 이 값을 다시 그림

// 화면 폭(128px)을 넘지 않도록 공백 기준으로 줄바꿈해서 outLines에 채우고 줄 수를 반환
int wrapUTF8(const String &text, String outLines[], int maxLines) {
  int count = 0;
  int start = 0;
  String line = "";

  while (start <= (int)text.length() && count < maxLines) {
    int spaceIdx = text.indexOf(' ', start);
    String word = (spaceIdx == -1) ? text.substring(start) : text.substring(start, spaceIdx);
    String candidate = line.length() == 0 ? word : (line + " " + word);

    if (u8g2.getUTF8Width(candidate.c_str()) > 128 && line.length() > 0) {
      outLines[count++] = line;
      line = word;
    } else {
      line = candidate;
    }

    if (spaceIdx == -1) break;
    start = spaceIdx + 1;
  }

  if (line.length() > 0 && count < maxLines) {
    outLines[count++] = line;
  }
  return count;
}

// 화면 아래쪽에 이퀄라이저 막대를 그림. 매 프레임 각 막대 높이를 랜덤하게 조금씩 흔들어 지직이는 느낌을 냄
void drawSpectrumBars() {
  for (int i = 0; i < BAR_COUNT; i++) {
    barHeights[i] += random(-3, 4);   // 이전 높이 기준으로 랜덤하게 위아래 (random walk)
    if (barHeights[i] < BAR_MIN_HEIGHT) barHeights[i] = BAR_MIN_HEIGHT;
    if (barHeights[i] > BAR_MAX_HEIGHT) barHeights[i] = BAR_MAX_HEIGHT;

    int x = i * BAR_WIDTH;
    int barTop = 64 - barHeights[i];
    u8g2.drawBox(x, barTop, BAR_WIDTH - 1, barHeights[i]);  // -1: 막대 사이 살짝 틈을 둠
  }
}

// 화면 아래쪽에 부드럽게 이어지는 파도를 그림. sin 곡선이 옆으로 흐르면서(wavePhase),
// 진폭도 천천히 커졌다 작아졌다 해서(waveAmpPhase) 파도가 밀려왔다 쓸려가는 느낌을 냄
void drawWave() {
  wavePhase += 0.12;
  waveAmpPhase += 0.015;

  float amplitude = 5 + 4 * sin(waveAmpPhase);  // 1~9px 사이에서 천천히 오르내림
  int baseline = 64 - 8;

  for (int x = 0; x < 128; x++) {
    float y = baseline - amplitude * sin(x * 0.12 + wavePhase);
    int yi = (int)y;
    u8g2.drawVLine(x, yi, 64 - yi);  // yi부터 화면 맨 아래까지 채워서 파도 실루엣처럼 보이게 함
  }
}

// ---------- 턴테이블(레코드판) 배경 ----------
const float DISC_CX = 46, DISC_CY = 62, DISC_RX = 60, DISC_RY = 16;
const float LABEL_SCALE = 0.22;
const float GROOVE_SCALES[] = {0.36, 0.52, 0.66, 0.78, 0.89, 1.0};
const int GROOVE_COUNT = 6;
const unsigned long ROTATION_MS = 5000;

// 레코드판 타원 위의 한 점을 계산 (라벨 바늘, 홈 반지름 계산 등에 공용으로 씀)
void ellipsePoint(float scale, float angle, int &outX, int &outY) {
  outX = (int)round(DISC_CX + cos(angle) * DISC_RX * scale);
  outY = (int)round(DISC_CY + sin(angle) * DISC_RY * scale);
}

void drawVinylRecord(unsigned long now) {
  for (int i = 0; i < GROOVE_COUNT; i++) {
    u8g2.drawEllipse((int)DISC_CX, (int)DISC_CY,
                      (int)(DISC_RX * GROOVE_SCALES[i]), (int)(DISC_RY * GROOVE_SCALES[i]),
                      U8G2_DRAW_ALL);
  }

  // 가운데 라벨: 꽉 채운 타원
  int labelRx = (int)(DISC_RX * LABEL_SCALE);
  int labelRy = (int)(DISC_RY * LABEL_SCALE);
  u8g2.drawFilledEllipse((int)DISC_CX, (int)DISC_CY, labelRx, labelRy, U8G2_DRAW_ALL);

  // 라벨 가장자리보다 살짝 안쪽에, 원형으로 안 채워진 얇은 링(미인쇄 테두리)
  u8g2.setDrawColor(0);
  int ringRx = (int)(labelRx * 0.86);
  int ringRy = (int)(labelRy * 0.86);
  u8g2.drawEllipse((int)DISC_CX, (int)DISC_CY, ringRx, ringRy, U8G2_DRAW_ALL);
  u8g2.drawEllipse((int)DISC_CX, (int)DISC_CY, ringRx - 1, ringRy - 1, U8G2_DRAW_ALL);
  u8g2.setDrawColor(1);

  // 회전 착시: 라벨 위의 짧은 바늘 하나가 계속 돎
  float angle = (float)(now % ROTATION_MS) / ROTATION_MS * 2 * PI - PI / 2;
  int tx, ty;
  ellipsePoint(LABEL_SCALE * 0.95f, angle, tx, ty);
  u8g2.setDrawColor(0);
  u8g2.drawLine((int)DISC_CX, (int)DISC_CY, tx, ty);
  u8g2.setDrawColor(1);
}

// u8g2는 선 두께 지정이 안 되므로, y를 살짝 어긋나게 여러 번 그어서 두꺼운 선을 흉내냄
void drawThickLine(int x0, int y0, int x1, int y1, int thickness) {
  int half = thickness / 2;
  for (int o = -half; o <= half; o++) {
    u8g2.drawLine(x0, y0 + o, x1, y1 + o);
  }
}

void drawTonearm() {
  // 피벗은 둥근 허브 하나. 암은 허브 왼쪽에서, 카운터웨이트는 반대편(오른쪽) 축 끝에 달림
  const int pivotX = 121, pivotY = 40;
  const int elbowX = 106, elbowY = 45;
  const int tipX = 82, tipY = 50;
  const int hubR = 3;

  u8g2.drawDisc(pivotX, pivotY, hubR, U8G2_DRAW_ALL);
  u8g2.setDrawColor(0);
  u8g2.drawCircle(pivotX, pivotY, hubR, U8G2_DRAW_ALL);
  u8g2.setDrawColor(1);

  // 카운터웨이트: 짧은 축 + 원통, 몸통에 음영 띠 2개
  int cwX = pivotX + 9, cwY = pivotY;
  u8g2.drawLine(pivotX + hubR, pivotY, cwX, cwY);
  u8g2.drawBox(cwX - 1, cwY - 5, 7, 10);
  u8g2.setDrawColor(0);
  u8g2.drawBox(cwX - 1, cwY - 3, 7, 1);
  u8g2.drawBox(cwX - 1, cwY + 1, 7, 1);
  u8g2.setDrawColor(1);

  // 암: 허브 왼쪽에서 시작, 두껍게 그리고 한쪽 가장자리에 음영선을 붙여 둥근 튜브처럼 보이게 함
  int armStartX = pivotX - hubR, armStartY = pivotY;
  drawThickLine(armStartX, armStartY, elbowX, elbowY, 3);
  drawThickLine(elbowX, elbowY, tipX, tipY, 3);
  u8g2.setDrawColor(0);
  u8g2.drawLine(armStartX, armStartY - 1, elbowX, elbowY - 1);
  u8g2.drawLine(elbowX, elbowY - 1, tipX, tipY - 1);
  u8g2.setDrawColor(1);

  // 헤드셸(카트리지) 블록: 팔 방향에 맞춰 회전된 사각형 (삼각형 2개로 구성)
  float armAngle = atan2((float)(tipY - elbowY), (float)(tipX - elbowX));
  float ca = cos(armAngle), sa = sin(armAngle);
  int p1x, p1y, p2x, p2y, p3x, p3y, p4x, p4y;
  auto rotatePoint = [&](float lx, float ly, int &ox, int &oy) {
    ox = tipX + (int)round(lx * ca - ly * sa);
    oy = tipY + (int)round(lx * sa + ly * ca);
  };
  rotatePoint(-2, -3, p1x, p1y);
  rotatePoint(11, -3, p2x, p2y);
  rotatePoint(11, 3, p3x, p3y);
  rotatePoint(-2, 3, p4x, p4y);
  u8g2.drawTriangle(p1x, p1y, p2x, p2y, p3x, p3y);
  u8g2.drawTriangle(p1x, p1y, p3x, p3y, p4x, p4y);

  // 카트리지 윗면 절반을 살짝 어둡게 해서 윗면/옆면이 나뉘어 보이는 입체감을 줌
  int q1x, q1y, q2x, q2y, q3x, q3y, q4x, q4y;
  rotatePoint(-2, -3, q1x, q1y);
  rotatePoint(11, -3, q2x, q2y);
  rotatePoint(11, -1, q3x, q3y);
  rotatePoint(-2, -1, q4x, q4y);
  u8g2.setDrawColor(0);
  u8g2.drawTriangle(q1x, q1y, q2x, q2y, q3x, q3y);
  u8g2.drawTriangle(q1x, q1y, q3x, q3y, q4x, q4y);
  u8g2.setDrawColor(1);

  // 바늘(스타일러스) 끝
  int n1x = tipX + (int)round(11 * cos(armAngle));
  int n1y = tipY + (int)round(11 * sin(armAngle));
  int n2x = tipX + (int)round(15 * cos(armAngle + 0.35f));
  int n2y = tipY + (int)round(15 * sin(armAngle + 0.35f));
  u8g2.drawLine(n1x, n1y, n2x, n2y);
}

// 버튼(GPIO4, 눌리면 GND로 연결됨)을 디바운스해서 눌리는 순간에만 배경 모드를 다음 것으로 전환
void checkButton() {
  int raw = digitalRead(BUTTON_PIN);
  if (raw != buttonRawState) {
    buttonLastEdgeMs = millis();
  }
  if (millis() - buttonLastEdgeMs > BUTTON_DEBOUNCE_MS && raw != buttonStableState) {
    buttonStableState = raw;
    if (buttonStableState == LOW) {  // 풀업 상태라 눌리면 LOW가 됨
      backgroundMode = (backgroundMode + 1) % NUM_BACKGROUND_MODES;
    }
  }
  buttonRawState = raw;
}

// 점들이 위에서 아래로 천천히 떨어지다가 maxY에 닿으면 위쪽 랜덤한 위치에서 다시 시작
// (턴테이블 모드에서는 레코드판 근처까지 내려오면 지저분해 보여서 maxY를 작게 줌)
void drawSnow(int maxY = 64) {
  for (int i = 0; i < SNOW_COUNT; i++) {
    if (snowY[i] > maxY) snowY[i] = maxY;  // 모드 전환 직후 범위를 벗어나 있으면 안으로 당겨옴
    u8g2.drawPixel(snowX[i], snowY[i]);
    snowY[i] += 1;
    if (snowY[i] >= maxY) {
      snowY[i] = 0;
      snowX[i] = random(0, 128);
    }
  }
}

// 가사(또는 간주 중 곡 제목)를 막대 위쪽 영역(TEXT_AREA_HEIGHT)에 가로/세로 중앙 정렬로 그림
// isTitleMode에 따라 폰트 크기를 바꾼다 (제목은 크게, 가사는 작게)
void drawCenteredText(const String &text) {
  u8g2.setFont(isTitleMode ? u8g2_font_gulim16_t_korean2 : u8g2_font_gulim11_t_korean2);
  int lineHeight = isTitleMode ? TITLE_LINE_HEIGHT : LYRIC_LINE_HEIGHT;
  int maxLines = isTitleMode ? TITLE_MAX_LINES : LYRIC_MAX_LINES;

  String lines[MAX_LINES_CAP];
  int count = wrapUTF8(text, lines, maxLines);
  if (count == 0) return;

  int blockHeight = count * lineHeight;
  int startY = (TEXT_AREA_HEIGHT - blockHeight) / 2 + lineHeight;  // 첫 줄의 baseline y좌표

  for (int i = 0; i < count; i++) {
    int width = u8g2.getUTF8Width(lines[i].c_str());
    int x = (128 - width) / 2;
    if (x < 0) x = 0;
    u8g2.drawUTF8(x, startY + i * lineHeight, lines[i].c_str());
  }
}

void setup() {
  // PC와 같은 속도(baud rate)로 통신하기로 정하는 것. 시리얼 모니터도 115200으로 맞춰야 함
  // (시계처럼 실시간으로 맞추는 "동기화"가 아니라, 서로 같은 숫자를 미리 약속해두는 것)
  Serial.begin(115200);
  randomSeed(micros());  // 매 부팅마다 노이즈 패턴이 다르게 나오도록 시드를 다르게 줌

  u8g2.begin();  // 디스플레이에 초기화 명령을 보내 사용 가능한 상태로 만듦
  // 폰트는 drawCenteredText()에서 isTitleMode에 따라 매 프레임 다시 설정함

  pinMode(BUTTON_PIN, INPUT_PULLUP);  // 버튼 안 눌렀을 때 HIGH, 누르면 GND에 연결돼 LOW

  currentText = "준비완료";
  for (int i = 0; i < BAR_COUNT; i++) {
    barHeights[i] = BAR_MAX_HEIGHT / 2;  // 막대 초기 높이
  }
  for (int i = 0; i < SNOW_COUNT; i++) {
    snowX[i] = random(0, 128);
    snowY[i] = random(0, 64);  // 시작 높이를 흩어놔서 한꺼번에 떨어지지 않게 함
  }

  Serial.println("Ready. 시리얼 모니터에 텍스트를 입력하고 엔터를 누르면 OLED에 표시됩니다.");
}

const char* LYRIC_PREFIX = "LYRIC|";        // PC에서 보내는 프로토콜: "LYRIC|가사내용"
const int LYRIC_PREFIX_LEN = 6;              // strlen("LYRIC|")
const char* TITLE_PREFIX = "TITLE|";        // 간주 중 곡 제목 표시용: "TITLE|제목"
const int TITLE_PREFIX_LEN = 6;              // strlen("TITLE|")

const unsigned long FRAME_INTERVAL_MS = 80;  // 배경 애니메이션 프레임 간격 (약 12fps)
unsigned long lastFrameMs = 0;

void loop() {
  if (Serial.available() > 0) {                 // PC에서 보낸 데이터가 도착해 있는지 확인
    String line = Serial.readStringUntil('\n');  // 줄바꿈 문자가 올 때까지 들어온 문자들을 하나의 문자열로 읽음
    line.trim();                                  // 끝에 남는 '\r'이나 앞뒤 공백 제거

    if (line.startsWith(LYRIC_PREFIX)) {
      currentText = line.substring(LYRIC_PREFIX_LEN);  // prefix를 떼고 실제 가사 내용만 추출해 저장해둠
      isTitleMode = false;

      Serial.print("Displayed: ");
      Serial.println(currentText);               // 확인용으로 PC 쪽에도 같은 내용을 되돌려 보여줌
    } else if (line.startsWith(TITLE_PREFIX)) {
      currentText = line.substring(TITLE_PREFIX_LEN);
      isTitleMode = true;

      Serial.print("Displayed (title): ");
      Serial.println(currentText);
    }
  }

  checkButton();  // 프레임 주기와 상관없이 매 loop마다 확인해야 짧게 눌러도 안 놓침

  unsigned long now = millis();
  if (now - lastFrameMs >= FRAME_INTERVAL_MS) {   // 매 프레임마다 배경 애니메이션 + 현재 가사를 다시 그림
    lastFrameMs = now;

    u8g2.clearBuffer();
    if (backgroundMode == BG_MODE_BARS) {
      drawSnow();
      drawSpectrumBars();
    } else if (backgroundMode == BG_MODE_WAVE) {
      drawSnow();
      drawWave();
    } else {
      drawSnow(40);  // 턴테이블 모드는 레코드판 근처까지 안 내려오게 범위를 좁힘
      drawVinylRecord(now);
      drawTonearm();
    }
    drawCenteredText(currentText);
    u8g2.sendBuffer();
  }
}
