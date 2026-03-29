"""
Skill 2: Aggregator & FX Converter
두 포트폴리오를 합산하고, USD→KRW 환율 변환 후
가족 총 자산(Total Net Worth)과 MoM 변동률을 계산합니다.
결과를 data/portfolio_total.json에 저장합니다.
"""

import json
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

USER_PORTFOLIO = DATA_DIR / "portfolio_user.json"
HUSBAND_PORTFOLIO = DATA_DIR / "portfolio_husband.json"
TOTAL_PORTFOLIO = DATA_DIR / "portfolio_total.json"


def get_usd_krw_rate() -> float:
    """환율 API로 현재 USD/KRW 환율을 조회합니다 (무료 API 사용)."""
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        with urllib.request.urlopen(url, timeout=5) as res:
            data = json.loads(res.read())
        rate = data["rates"]["KRW"]
        print(f"💱 USD/KRW 환율: {rate:,.0f}원")
        return rate
    except Exception as e:
        print(f"⚠️  환율 조회 실패 ({e}), 기본값 1,450원 사용")
        return 1450.0


def load_portfolio(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def to_krw(value: float, currency: str, fx_rate: float) -> float:
    """USD 자산을 KRW로 환산합니다."""
    if currency.upper() == "USD":
        return value * fx_rate
    return value


def get_category_breakdown(holdings: list, currency: str, fx_rate: float) -> dict:
    """카테고리별 자산 비중을 계산합니다."""
    breakdown = {}
    for h in holdings:
        cat = h.get("category", "기타")
        val_krw = to_krw(h.get("current_value", 0), currency, fx_rate)
        breakdown[cat] = breakdown.get(cat, 0) + val_krw
    return breakdown


def load_previous_total() -> float:
    """이전 달 총 자산을 불러옵니다 (MoM 계산용)."""
    if not TOTAL_PORTFOLIO.exists():
        return 0.0
    with open(TOTAL_PORTFOLIO, encoding="utf-8") as f:
        data = json.load(f)
    history = data.get("monthly_history", [])
    if len(history) < 2:
        return 0.0
    # 가장 최근 이전 달 데이터
    return history[-2].get("total_value_krw", 0.0)


def aggregate():
    """두 포트폴리오를 합산하여 portfolio_total.json을 생성합니다."""
    fx_rate = get_usd_krw_rate()
    today = date.today().isoformat()

    user = load_portfolio(USER_PORTFOLIO)
    husband = load_portfolio(HUSBAND_PORTFOLIO)

    # 각 포트폴리오 KRW 환산 총액
    user_currency = user.get("account", {}).get("currency", "KRW")
    husband_currency = husband.get("account", {}).get("currency", "USD")

    user_summary = user.get("summary", {})
    husband_summary = husband.get("summary", {})

    # USD 필드명 처리 (portfolio_husband는 _usd suffix 사용 가능)
    def get_val(summary: dict, key: str, currency: str) -> float:
        val = summary.get(key) or summary.get(f"{key}_usd", 0)
        return to_krw(val or 0, currency, fx_rate)

    user_total_krw = get_val(user_summary, "total_value", user_currency)
    user_cost_krw = get_val(user_summary, "total_cost", user_currency)
    husband_total_krw = get_val(husband_summary, "total_value", husband_currency)
    husband_cost_krw = get_val(husband_summary, "total_cost", husband_currency)

    family_total_krw = user_total_krw + husband_total_krw
    family_cost_krw = user_cost_krw + husband_cost_krw
    family_pnl_krw = family_total_krw - family_cost_krw
    family_pnl_pct = (family_pnl_krw / family_cost_krw * 100) if family_cost_krw else 0

    # MoM 계산
    prev_total = load_previous_total()
    mom_krw = family_total_krw - prev_total if prev_total else 0
    mom_pct = (mom_krw / prev_total * 100) if prev_total else 0

    # 카테고리 합산
    user_cats = get_category_breakdown(user.get("holdings", []), user_currency, fx_rate)
    husband_cats = get_category_breakdown(husband.get("holdings", []), husband_currency, fx_rate)
    all_cats = {**user_cats}
    for cat, val in husband_cats.items():
        all_cats[cat] = all_cats.get(cat, 0) + val

    # 기존 히스토리 불러오기
    existing = load_portfolio(TOTAL_PORTFOLIO)
    history = existing.get("monthly_history", [])

    # 이번 달 스냅샷 추가 (같은 날짜면 덮어씀)
    snapshot = {
        "date": today,
        "total_value_krw": round(family_total_krw),
        "user_value_krw": round(user_total_krw),
        "husband_value_krw": round(husband_total_krw),
        "fx_rate_usd_krw": fx_rate,
    }
    history = [h for h in history if h["date"] != today]
    history.append(snapshot)
    history = sorted(history, key=lambda x: x["date"])

    total_data = {
        "last_updated": today,
        "fx_rate_usd_krw": fx_rate,
        "summary": {
            "family_total_krw": round(family_total_krw),
            "family_cost_krw": round(family_cost_krw),
            "family_pnl_krw": round(family_pnl_krw),
            "family_pnl_pct": round(family_pnl_pct, 2),
            "user_total_krw": round(user_total_krw),
            "husband_total_krw": round(husband_total_krw),
            "mom_krw": round(mom_krw),
            "mom_pct": round(mom_pct, 2),
        },
        "category_breakdown_krw": {k: round(v) for k, v in sorted(
            all_cats.items(), key=lambda x: x[1], reverse=True
        )},
        "monthly_history": history,
    }

    TOTAL_PORTFOLIO.parent.mkdir(parents=True, exist_ok=True)
    with open(TOTAL_PORTFOLIO, "w", encoding="utf-8") as f:
        json.dump(total_data, f, ensure_ascii=False, indent=2)

    print(f"\n📊 가족 총 자산 현황 ({today})")
    print(f"  총 자산:     {family_total_krw:>15,.0f} 원")
    print(f"  총 투자금:   {family_cost_krw:>15,.0f} 원")
    print(f"  총 평가손익: {family_pnl_krw:>+15,.0f} 원 ({family_pnl_pct:+.2f}%)")
    print(f"  MoM 변동:    {mom_krw:>+15,.0f} 원 ({mom_pct:+.2f}%)")
    print(f"  USD/KRW:     {fx_rate:>15,.0f}")
    print(f"\n✅ 저장 완료: {TOTAL_PORTFOLIO}")

    return total_data


if __name__ == "__main__":
    aggregate()
