# CLAUDE.md

이 파일은 이 저장소에서 자산 관리 및 투자 트래킹을 수행하는 AI를 위한 지침서입니다.


## Project Overview
사용자의 주식 계좌 현황(스크린샷 및 텍스트)을 분석하여 매수/매도 이력을 추적하고, 현재 자산 현황과 섹터별 비중 등 통계 리포트를 생성하는 개인 금융 관리 프로젝트입니다. 
<!-- Describe what this project does and its primary purpose -->

## Commands
1. 데이터 입력 및 동기화 (Data Entry)

스크린샷 분석: 사용자가 올린 증권사 앱 스크린샷에서 종목명, 수량, 평단가, 수익률을 정확히 추출하여 기록합니다.

거래 기록: 사용자가 "테슬라 10주 매수"와 같이 텍스트로 입력하면 즉시 기존 포트폴리오 데이터에 반영합니다.

데이터 우선순위: 텍스트 입력과 스크린샷 데이터가 충돌할 경우, 스크린샷의 정보를 최우선으로 하여 데이터를 보정합니다. (계좌가 분산되어 있어 발생할 수 있는 실수를 방지하기 위함)

2. 리포팅 (Reporting)

단순 현황 보고: 현재 보유 중인 종목 리스트, 수량, 평균 단가를 요약합니다.

주간 통계 리포트 (매주 1회) 혹은 요청 시 마다

 - 전체 자산 규모 및 전주 대비 변동성 분석

 - 섹터별 투자 비중 (Tech, Energy, Finance 등) 시각화 데이터 준비

 - 수익률 상/하위 종목 브리핑


### Build
```bash
# Add build command here
```

### Test
```bash
# Run all tests
# Run a single test
```

### Lint / Format
```bash
# Add lint/format commands here
```

## Architecture
portfolio.json: 모든 자산 현황과 거래 이력이 저장되는 마스터 데이터 파일입니다.

reports/: 생성된 주간/월간 리포트가 저장되는 디렉토리입니다.
<!-- Describe the high-level structure: major modules, data flow, key design decisions -->

## Key Conventions & Rules
정확성: 수량과 평단가는 소수점까지 정확하게 기록해야 합니다.

통화 구분: 원화(KRW)와 외화(USD) 자산을 명확히 구분하여 기록합니다.

톤앤매너: 보고는 명확하고 간결하게 하되, 사용자의 투자 성향에 맞춘 인사이트를 짧게 덧붙입니다.

프라이버시: 민감한 금융 정보이므로 외부 유출 없이 내부 데이터 저장소 내에서만 처리합니다.

<!-- Language, framework versions, naming conventions, patterns used in this project -->
