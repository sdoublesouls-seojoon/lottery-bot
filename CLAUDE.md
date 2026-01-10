# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

동행복권(dhlottery.co.kr) 자동 구매 및 당첨 확인 봇입니다. GitHub Actions를 통해 매주 자동으로 로또645를 구매하고 당첨을 확인하여 Slack/Discord로 알림을 보냅니다.

## 필수 커맨드

### 의존성 설치
```bash
make install
# 또는
pip3 install -r requirements.txt
```

### 로또 구매
```bash
make buy
# 또는
python3 controller.py buy
```

### 당첨 확인
```bash
make check
# 또는
python3 controller.py check
```

## 환경 변수 설정

`.env` 파일 또는 GitHub Secrets에 다음 변수를 설정해야 합니다:
- `USERNAME`: 동행복권 사용자 ID
- `PASSWORD`: 동행복권 비밀번호
- `COUNT`: 구매할 로또 게임 수 (1-5)
- `SLACK_WEBHOOK_URL`: Slack 웹훅 URL (선택)
- `DISCORD_WEBHOOK_URL`: Discord 웹훅 URL (선택)

알림은 Slack을 우선적으로 사용하며, 없을 경우 Discord를 사용합니다.

## 아키텍처

### 핵심 모듈

1. **controller.py** - 메인 엔트리포인트
   - `buy()`: 로또 구매 프로세스 실행
   - `check()`: 당첨 확인 프로세스 실행
   - 환경 변수 로드 및 AuthController 초기화
   - 알림 플랫폼 선택 로직 (Slack 우선, 없으면 Discord)

2. **auth.py** - 인증 관리
   - `AuthController`: 동행복권 로그인 처리
   - RSA 공개키 기반 암호화 로그인 구현 (pyjsbn-rsa 사용)
   - 세션 쿠키(DHJSESSIONID) 관리
   - 로그인 프로세스:
     1. 로그인 페이지 접속으로 초기 세션 획득
     2. RSA 공개키 조회 (`selectRsaModulus.do`)
     3. 사용자 ID와 비밀번호를 RSA 암호화
     4. 로그인 요청 (`securityLoginCheck.do`)
     5. 세션 쿠키 저장

3. **lotto645.py** - 로또645 관련 기능
   - `buy_lotto645()`: 로또 구매 (자동/수동 모드)
   - `check_winning()`: 당첨 확인
   - `get_balance()`: 예치금 잔액 조회
   - 중요 프로세스:
     - `_getRequirements()`: TotalGame.jsp 호출 후 game645.do에서 필수 파라미터 추출
     - `_get_round()`: 현재 회차 계산
     - `_try_buying()`: execBuy.do API 호출

4. **notification.py** - 알림 전송
   - Slack/Discord 웹훅 지원
   - 로또 구매 완료 메시지
   - 당첨 결과 메시지 (당첨 번호 포맷팅 포함)

5. **HttpClient.py** - HTTP 클라이언트
   - 싱글톤 패턴으로 세션 관리
   - 모든 HTTP 요청은 동일한 세션을 사용하여 쿠키 유지

### 중요한 구현 세부사항

#### RSA 암호화
- 동행복권 로그인은 RSA 공개키 암호화를 사용합니다
- `pyjsbn-rsa` 라이브러리로 JavaScript의 jsbn과 호환되는 암호화 구현
- 사용자 ID와 비밀번호 모두 암호화가 필요합니다

#### 세션 관리
- `HttpClientSingleton`을 통해 전체 애플리케이션에서 단일 세션 유지
- 모든 모듈(`auth`, `lotto645`, `win720`)이 동일한 세션 인스턴스 공유
- 세션 쿠키는 `DHJSESSIONID` 이름으로 관리됩니다

#### 로또 구매 흐름
1. `TotalGame.jsp?LottoId=LO40` 호출 (세션 초기화)
2. `game645.do` GET 요청으로 `ROUND_DRAW_DATE`, `WAMT_PAY_TLMT_END_DT` 파라미터 추출
3. `egovUserReadySocket.json` POST 요청으로 `ready_ip` 획득
4. `execBuy.do`로 구매 실행

#### 당첨 확인 흐름
1. 지난 7일간 구매 내역 조회 (`lottoBuyList`)
2. 당첨 건이 있으면 상세 정보 조회 (`lotto645Detail`)
3. HTML 파싱하여 각 게임별 당첨 번호 및 등수 추출

## GitHub Actions 워크플로우

- **buy_lotto.yml**: 매주 월요일 19:00 KST (cron: `0 10 * * 1`)
- **check_winning.yml**: 매주 토요일 22:00 KST (cron: `0 13 * * 6`)

두 워크플로우 모두 `workflow_dispatch`로 수동 실행 가능합니다.

## 주의사항

- 연금복권(win720) 관련 코드는 현재 주석 처리되어 사용하지 않습니다
- 로또645만 지원됩니다
- 자동 모드만 구현되어 있으며, 수동 모드는 `NotImplementedError`를 발생시킵니다
- 구매 가능한 게임 수는 1-5개로 제한됩니다
- Python 3.9 버전 사용을 권장합니다
