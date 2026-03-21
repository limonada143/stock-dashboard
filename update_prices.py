#!/usr/bin/env python3
"""
KRX 실시간 주가를 가져와 portfolio.json의 현재가를 자동 업데이트하는 스크립트
사용법: python update_prices.py

필요 패키지: pip install pykrx
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from pykrx import stock
except ImportError:
    print("❌ pykrx 미설치. 아래 명령어로 설치해주세요:")
    print("   pip install pykrx")
    exit(1)

PORTFOLIO_PATH = Path(__file__).parent / "portfolio.json"

# portfolio.json의 종목명 → KRX 티커코드 매핑
TICKER_MAP = {
    "ACE 원자력TOP10":              "433500",
    "TIGER 반도체TOP10":            "396500",
    "KODEX 반도체":                 "091160",
    "KODEX 200":                    "069500",
    "HANARO 원자력iSelect":         "434730",
    "TIGER 코리아시전략기기TOP3플러스": "458730",  # TIGER 코리아AI전력기기TOP3플러스
    "TIGER 삼성그룹":               "136480",
    "TIGER K방산&우주":             "463250",
    "KODEX 증권":                   "102970",
    "ACE 코스닥150":                "354500",
    "TIGER 현대차그룹플러스":       "138540",
    "TIME 미국나스닥100액티브":     "426030",
    "SOL 조선TOP3플러스":           "466920",
    "SOL 조선기자재":               "481180",
    "TIME K바이오액티브":           "463050",
}


def get_latest_trading_date() -> str:
    """가장 최근 영업일 반환 (오늘 또는 어제)"""
    today = date.today()
    # 주말이면 금요일로
    if today.weekday() == 6:  # 일요일
        today -= timedelta(days=2)
    elif today.weekday() == 5:  # 토요일
        today -= timedelta(days=1)
    return today.strftime("%Y%m%d")


def fetch_current_prices(date_str: str) -> dict:
    """pykrx로 ETF 현재가 조회"""
    print(f"\n📡 KRX에서 {date_str} 종가 조회 중...")
    prices = {}

    for name, ticker in TICKER_MAP.items():
        try:
            df = stock.get_market_ohlcv_by_date(date_str, date_str, ticker)
            if not df.empty:
                close_price = int(df["종가"].iloc[-1])
                prices[name] = close_price
                print(f"  ✅ {name}: {close_price:,}원")
            else:
                print(f"  ⚠️  {name}: 데이터 없음 (거래정지 또는 날짜 오류)")
                prices[name] = None
        except Exception as e:
            print(f"  ❌ {name}: 조회 실패 ({e})")
            prices[name] = None

    return prices


def update_portfolio(prices: dict, date_str: str):
    """portfolio.json 현재가 업데이트"""
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    updated_count = 0
    total_value = 0

    for holding in portfolio["holdings"]:
        name = holding["name"]
        new_price = prices.get(name)

        if new_price and new_price > 0:
            old_price = holding.get("current_price", 0)
            holding["current_price"] = new_price
            holding["current_value"] = int(new_price * holding["shares"])

            # 손익 재계산
            cost = holding["avg_price"] * holding["shares"]
            holding["unrealized_pnl"] = holding["current_value"] - cost
            holding["unrealized_pnl_pct"] = round(
                (holding["current_value"] - cost) / cost * 100, 2
            )
            total_value += holding["current_value"]
            updated_count += 1

            change = new_price - old_price
            arrow = "▲" if change >= 0 else "▼"
            print(f"  {arrow} {name}: {old_price:,} → {new_price:,}원 ({change:+,})")
        else:
            total_value += holding.get("current_value", 0)

    # 전체 summary 업데이트
    total_cost = sum(h["avg_price"] * h["shares"] for h in portfolio["holdings"])
    total_pnl = total_value - total_cost
    portfolio["summary"]["total_value"] = total_value
    portfolio["summary"]["total_cost"] = int(total_cost)
    portfolio["summary"]["unrealized_pnl"] = int(total_pnl)
    portfolio["summary"]["unrealized_pnl_pct"] = round(total_pnl / total_cost * 100, 2)

    # 날짜 업데이트
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    portfolio["account"]["last_updated"] = formatted_date

    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)

    return portfolio, updated_count


def print_final_summary(portfolio: dict):
    """최종 요약 출력"""
    s = portfolio["summary"]
    print("\n" + "=" * 55)
    print("📊 업데이트 완료 - 포트폴리오 현황")
    print("=" * 55)
    print(f"{'총 평가금액':<12}: ₩{s['total_value']:>15,.0f}")
    print(f"{'총 매입금액':<12}: ₩{s['total_cost']:>15,.0f}")
    print(f"{'평가 손익':<12}: ₩{s['unrealized_pnl']:>15,.0f}")
    print(f"{'수익률':<12}: {s['unrealized_pnl_pct']:>14.2f}%")
    print("=" * 55)

    print("\n[수익률 TOP 5 ▲]")
    sorted_holdings = sorted(
        portfolio["holdings"], key=lambda x: x["unrealized_pnl_pct"], reverse=True
    )
    for h in sorted_holdings[:5]:
        print(f"  {h['name']}: {h['unrealized_pnl_pct']:+.2f}%")

    print("\n[수익률 BOTTOM 5 ▼]")
    for h in sorted_holdings[-5:]:
        print(f"  {h['name']}: {h['unrealized_pnl_pct']:+.2f}%")


def main():
    print("=" * 55)
    print("🔄 포트폴리오 현재가 자동 업데이트")
    print("=" * 55)

    date_str = get_latest_trading_date()
    print(f"📅 기준일: {date_str[:4]}-{date_str[4:6]}-{date_str[6:]}")

    # 주가 조회
    prices = fetch_current_prices(date_str)

    # 업데이트
    print("\n💾 portfolio.json 업데이트 중...")
    portfolio, updated_count = update_portfolio(prices, date_str)

    print(f"\n✅ 총 {updated_count}개 종목 현재가 업데이트 완료!")
    print_final_summary(portfolio)


if __name__ == "__main__":
    main()
