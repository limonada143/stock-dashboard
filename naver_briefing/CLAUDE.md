# CLAUDE.md — naver_briefing

네이버 블로그 구독 + 프리미엄콘텐츠를 매일 아침 자동 수집하여
Claude로 묶어서 요약하고 텔레그램으로 전송하는 프로젝트.

## 흐름
1. Playwright로 네이버 로그인 (쿠키 캐시)
2. 이웃 블로그 새글 + 프리미엄콘텐츠 구독 피드 스크래핑
3. Claude API로 전체 묶어서 브리핑 요약
4. 텔레그램 전송
5. 매일 아침 크론으로 자동 실행

## 환경변수 (.env)
- `NAVER_ID`: 네이버 아이디
- `NAVER_PW`: 네이버 비밀번호
- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰
- `TELEGRAM_CHAT_ID`: 전송 대상 chat ID
