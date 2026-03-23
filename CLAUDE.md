# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

이 저장소에서 부부 자산 관리 및 투자 트래킹을 수행하고, 3-Tab 대시보드를 구축하는 AI를 위한 지침서입니다.

## Project Overview
사용자 및 배우자의 주식/자산 계좌 현황(스크린샷 및 텍스트)을 분석하여 매수/매도 이력을 추적하고, 매월 1회 총합 및 개별 자산 현황, 섹터별 비중, 전월 대비 변동성을 시각화하는 3-Tab 대시보드(Total, User, Husband) 리포트를 생성하는 부부 금융 관리 프로젝트입니다.

## Commands

### 대시보드 실행
```bash
streamlit run dashboard/app.py
```

### 가격 업데이트
```bash
python update_prices.py
```

### 스크린샷 분석
```bash
python analyze_screenshot.py
```

### 데이터 무결성 검사
```bash
pytest tests/
```

## Architecture

### 데이터 파일 (루트)
- `history.json`: 부부 합산 월별 총자산 히스토리 (`total_cost`, `total_value`, `unrealized_pnl`, `unrealized_pnl_pct`)
- `sector_history.json`: 섹터별 비중 히스토리
- `portfolio_husband.json`: 루트 레벨 남편 포트폴리오 마스터 데이터

### 데이터 파일 (dashboard/)
- `dashboard/portfolio_user.json`: User 자산 현황 및 거래 이력
- `dashboard/portfolio_husband.json`: Husband 자산 현황 및 거래 이력
- `dashboard/portfolio_total.json`: 부부 합산 월별 스냅샷

### 코드
- `dashboard/app.py`: Streamlit 3-Tab 대시보드 (Total / User / Husband)
- `skills/account_classifier.py`: 계좌 소유자(user/husband) 분류 유틸리티
- `skills/aggregator.py`: 포트폴리오 데이터 집계 유틸리티
- `skills/update_price.py`: 가격 업데이트 스크립트
- `analyze_screenshot.py`: 증권사 앱 스크린샷 파싱
- `reports/`: 월간 마크다운 리포트 저장소

## Key Conventions & Rules

### 데이터 입력 및 동기화
- **소유자 식별**: 모든 거래 이력과 자산 데이터에 `owner` 필드(`"user"` 또는 `"husband"`) 필수 명시
- **데이터 우선순위**: history.json에 기입된 날짜의 합계 > 스크린샷 > 텍스트 입력 순. 해당 날짜에 이미 값이 있으면 덮어쓰지 않음
- **total_cost 불변 원칙**: `history.json`의 `total_cost`는 실제 입출금 내역 발생 시에만 업데이트. 주식 가격 변동으로는 절대 수정하지 않음. 유저가 명시하지 않으면 직전 값 유지
- **total_value 업데이트**: 최신 주가 반영 시 새 날짜로 항목 추가(기존 항목 덮어쓰기 금지). `unrealized_pnl` = `total_value - total_cost`, `unrealized_pnl_pct` = `unrealized_pnl / total_cost * 100`

### 통화 및 환율
- KRW/USD 자산 구분 기록
- Total 대시보드에서는 실시간 환율 적용해 KRW 기준으로 합산

### 정확성
- 수량과 평단가는 소수점까지 정확하게 기록

### 톤앤매너
- 보고는 객관적·명확하게, 데이터 기반의 통찰(섹터 편중 등)을 짧게 덧붙임
