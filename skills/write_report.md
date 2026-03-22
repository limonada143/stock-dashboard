# Skill: 월간 포트폴리오 리포트 작성

## 트리거 조건
사용자가 다음과 같이 요청할 때 실행:
- "리포트 써줘", "리포트 생성해줘"
- "월간 리포트", "포트폴리오 리포트"
- "텔레그램으로 보내줘" (→ 리포트 생성 후 전송 포함)
- "MD 파일로 리포트 만들어줘"

---

## 데이터 소스

| 파일 | 용도 |
|---|---|
| `portfolio.json` | 아내 보유 종목, 계좌별 현황, summary |
| `portfolio_husband.json` | 남편 보유 종목, 계좌별 현황, summary |
| `history.json` | 월말 스냅샷 (note: "Users" / "Husband") |
| `sector_history.json` | 날짜별 섹터 합산 |

---

## 실행 순서

### 1. 데이터 수집
- `portfolio.json` → `summary.total_value`, `unrealized_pnl`, `unrealized_pnl_pct` 읽기
- `portfolio_husband.json` → 동일 필드 읽기
- `history.json`에서 직전 월말 스냅샷(note 기준 각각) → 전월 대비 변동 계산
- `sector_history.json` 최신 항목 → 섹터별 비중

### 2. 지표 계산

**부부 합산 수익률** — history.json 기반 실제 투입 원금 대비 현재 자산 비교:
```
총 투입 원금      = portfolio.json summary.total_cost
                  + portfolio_husband.json summary.total_cost
총 평가금액       = portfolio.json summary.total_value
                  + portfolio_husband.json summary.total_value
  (total_value는 익절 포함 사용자 수정값)
실제 수익         = 총 평가금액 - 총 투입 원금
실제 수익률(%)    = 실제 수익 / 총 투입 원금 * 100
```

**개인별 수익률 (아내/남편 탭)** — 현재 보유 종목 기준 미실현 손익:
```
미실현 수익       = portfolio.json summary.unrealized_pnl  (보유 종목 합산)
미실현 수익률(%)  = portfolio.json summary.unrealized_pnl_pct
```
> 두 탭의 수익률이 다른 이유: 개인 탭은 현재 보유 종목의 평단가 기준, 부부 합산은 익절분 포함 전체 투입 원금 기준.

**공통**:
```
전월 대비 변동액  = 현재 total_value - history.json 직전 월말 스냅샷 total_value
전월 대비 변동률  = 변동액 / 직전 스냅샷 total_value * 100
섹터 비중(%)      = sector_value / total * 100
```

### 3. 수익률 상위·하위 종목 추출
- 각 포트폴리오의 모든 holdings 순회
- `unrealized_pnl_pct` 기준 정렬
- 상위 3개, 하위 3개 추출

### 4. MD 파일 생성
- 저장 경로: `reports/YYYY-MM-DD.md`
- 파일명: 오늘 날짜 (예: `reports/2026-03-22.md`)
- `reports/` 폴더 없으면 생성

### 5. (선택) 텔레그램 전송
- 요청 시 Telegram Bot API로 전송
- Bot Token: 환경변수 또는 별도 설정 참조
- Chat ID: `7133279498`
- 메시지 형식: Markdown (parse_mode=Markdown)

---

## 리포트 MD 템플릿

```markdown
# 포트폴리오 리포트 — YYYY년 MM월 DD일

## 부부 합산

| 항목 | 금액 |
|---|---|
| 총 평가금액 | NNN,NNN,NNN 원 |
| 미실현 수익 | +NNN,NNN,NNN 원 |
| 수익률 | +NN.NN% |
| 전월 대비 | ±NNN,NNN,NNN 원 (±NN.NN%) |

---

## 아내 포트폴리오

| 항목 | 금액 |
|---|---|
| 총 평가금액 | NNN,NNN,NNN 원 |
| 미실현 수익 | +NNN,NNN,NNN 원 |
| 수익률 | +NN.NN% |
| 전월 대비 | ±NNN,NNN,NNN 원 (±NN.NN%) |

### 수익률 상위 3
| 종목 | 수익률 | 평가금액 |
|---|---|---|
| 종목A | +NN.NN% | NNN,NNN 원 |

### 수익률 하위 3
| 종목 | 수익률 | 평가금액 |
|---|---|---|
| 종목A | -NN.NN% | NNN,NNN 원 |

---

## 남편 포트폴리오

(동일 구조)

---


## 🔍 이달의 주요 변화 및 분석 (Update!)

### 1. 자산 변동 원인
* **자본 투입:** 이번 달 부부 합산 약 **NN,NNN,NNN원**의 추가 투입(또는 인출)이 식별되었습니다.
* **성장 동력:** 전체 자산 증가분의 **NN%**는 종목 수익 상승에 기인하며, 나머지는 추가 절약/입금에 의한 자산 형성입니다.

### 2. 섹터 리밸런싱 현황
* **비중 확대:** **[섹터명]** (전월 대비 +N.N%p) - 가장 가파른 비중 상승을 보였습니다.
* **비중 축소:** **[섹터명]** (전월 대비 -N.N%p) - 매도 또는 타 섹터 대비 상대적 하락으로 비중이 줄었습니다.

### 3. 특이사항
* **최고 효자 종목:** [아내/남편]의 **[종목명]**이 한 달간 **+NN.N%** 상승하며 전체 수익률을 견인했습니다.
* **주의 종목:** **[종목명]**의 하락폭(-NN.N%)이 커지며 하위권에 진입했습니다. 대응이 필요한지 검토가 필요합니다.

---
## 섹터 비중 (부부 합산)

| 섹터 | 금액 | 비중 |
|---|---|---|
| 반도체 | NNN,NNN,NNN 원 | NN.N% |
| AI/기술 | ... | ... |

---

## 메모

(사용자가 직접 작성)
```

---

## 텔레그램 전송 형식 (요약본)

Telegram은 4096자 제한이 있으므로 MD 전체 대신 **핵심 요약**만 전송:

```
📊 포트폴리오 리포트 — YYYY.MM.DD

💰 부부 합산
  총 자산: NNN,NNN만원 (전월比 ±NNN만원)
  수익률: +NN.NN% 
  [💡 분석] 순수 수익 +N만원 / 추가 투입 +N만원


👩 아내: NNN,NNN만원 (+NN.NN%)
👨 남편: NNN,NNN만원 (+NN.NN%)

📈 섹터 비중 변화
  TOP 1: [섹터명] NN.N% (전월比 ±N.N%p)
  TOP 2: [섹터명] NN.N% (전월比 ±N.N%p)
  TOP 3: [섹터명] NN.N% (전월比 ±N.N%p)
  *특이: [변화가 큰 섹터] 비중이 급증/급락함

🏆 수익 상위
  [아내] 종목A +NN.N%
  [남편] 종목B +NN.N%

💸 수익 하위
  [아내] 종목C -NN.N%
  [남편] 종목D -NN.N%

📝 한줄평: (예시) 이번 달은 [수익/입금]이 자산 성장을 견인했으며, [특정섹터] 비중이 눈에 띄게 늘었습니다. 

---

## 주의사항

- `history.json`의 직전 스냅샷은 `note` 필드("Users" / "Husband")로 구분
- 전월 대비는 가장 최근 스냅샷 기준 (당일 데이터 제외)
- 총 자산(`total_value`)은 익절 포함 사용자 수정값이므로 `portfolio.json`의 `summary.total_value`를 우선 사용
- 섹터 분류는 `sector_history.json` 최신 항목 기준 (없으면 `portfolio.json` 직접 집계)
