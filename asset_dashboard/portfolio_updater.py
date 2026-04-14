#!/usr/bin/env python3
"""
포트폴리오 업데이터 - 텔레그램 /stock 커맨드용

사용법:
  python portfolio_updater.py [user|husband] 종목명 [+|-]수량 [@평단가]

예시:
  python portfolio_updater.py TIGER반도체 +100 @23000        # 아내 매수
  python portfolio_updater.py 남편 KODEX200 +50 @45000      # 남편 매수
  python portfolio_updater.py TIGER반도체 -30               # 아내 매도
  python portfolio_updater.py                               # 현황 조회
"""

import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

BASE = Path(__file__).parent
PORTFOLIO_PATHS = {
    "user": BASE / "data" / "portfolio_user.json",
    "husband": BASE / "data" / "portfolio_husband.json",
}


def load_portfolio(owner: str) -> dict:
    with open(PORTFOLIO_PATHS[owner], encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(owner: str, data: dict) -> None:
    with open(PORTFOLIO_PATHS[owner], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_holding(holdings: list, name: str):
    """종목명으로 보유 종목 찾기 (부분 일치). (index, holding) 반환."""
    name_clean = name.lower().replace(" ", "")
    for i, h in enumerate(holdings):
        h_clean = h["name"].lower().replace(" ", "")
        if name_clean in h_clean or h_clean in name_clean:
            return i, h
    return -1, None


def recalculate_summary(portfolio: dict) -> None:
    """holdings 기반으로 summary.total_value / unrealized_pnl 재계산.
    total_cost는 절대 변경하지 않음 (CLAUDE.md 불변 원칙)."""
    holdings = portfolio["holdings"]
    s = portfolio["summary"]
    total_value = sum(h["shares"] * h["current_price"] for h in holdings)

    # KRW 또는 USD 필드 자동 감지
    if "total_cost" in s:
        total_cost = s["total_cost"]
        s["total_value"] = total_value
        s["unrealized_pnl"] = total_value - total_cost
        if total_cost:
            s["unrealized_pnl_pct"] = round(
                (total_value - total_cost) / total_cost * 100, 2
            )
    elif "total_cost_usd" in s:
        total_cost = s["total_cost_usd"]
        s["total_value_usd"] = total_value
        s["unrealized_pnl_usd"] = total_value - total_cost
        if total_cost:
            s["unrealized_pnl_pct"] = round(
                (total_value - total_cost) / total_cost * 100, 2
            )


def update_holding(
    owner: str, name: str, qty_delta: int, avg_price: Optional[float]
) -> str:
    portfolio = load_portfolio(owner)
    holdings = portfolio["holdings"]
    idx, holding = find_holding(holdings, name)
    owner_label = "아내" if owner == "user" else "남편"

    # 신규 종목
    if idx == -1:
        if qty_delta > 0 and avg_price is not None:
            new_holding = {
                "name": name,
                "ticker": name.replace(" ", ""),
                "shares": qty_delta,
                "avg_price": avg_price,
                "current_price": avg_price,
                "current_value": qty_delta * avg_price,
                "unrealized_pnl": 0,
                "unrealized_pnl_pct": 0.0,
                "type": "ETF",
                "category": "기타",
            }
            holdings.append(new_holding)
            recalculate_summary(portfolio)
            save_portfolio(owner, portfolio)
            return (
                f"✅ {owner_label} 신규 추가: {name}\n"
                f"   {qty_delta}주 @{avg_price:,.0f}원"
            )
        elif qty_delta > 0:
            return f"❌ 신규 종목 매수 시 평단가(@가격)가 필요합니다."
        else:
            return f"❌ '{name}' 종목을 찾을 수 없습니다."

    prev_shares = holding["shares"]
    prev_avg = holding["avg_price"]
    display_name = holding["name"]

    if qty_delta > 0:  # 매수
        if avg_price is None:
            return "❌ 매수 시 평단가(@가격)가 필요합니다.\n예: /stock TIGER반도체 +100 @23000"
        new_shares = prev_shares + qty_delta
        new_avg = round(
            (prev_shares * prev_avg + qty_delta * avg_price) / new_shares, 2
        )
        holding["shares"] = new_shares
        holding["avg_price"] = new_avg
        msg = (
            f"✅ {owner_label} {display_name} 매수\n"
            f"   +{qty_delta}주 @{avg_price:,.0f}원\n"
            f"   → 총 {new_shares}주, 평단 {new_avg:,.0f}원"
        )
    else:  # 매도
        new_shares = prev_shares + qty_delta  # qty_delta is negative
        if new_shares < 0:
            return f"❌ 보유 수량({prev_shares}주)보다 많이 매도할 수 없습니다."
        if new_shares == 0:
            holdings.pop(idx)
            recalculate_summary(portfolio)
            save_portfolio(owner, portfolio)
            return (
                f"✅ {owner_label} {display_name} 전량 매도\n"
                f"   -{prev_shares}주 (포지션 청산)"
            )
        holding["shares"] = new_shares
        msg = (
            f"✅ {owner_label} {display_name} 매도\n"
            f"   {qty_delta}주 → 잔여 {new_shares}주, 평단 {prev_avg:,.0f}원"
        )

    # current_value / unrealized_pnl 갱신
    holding["current_value"] = holding["shares"] * holding["current_price"]
    cost_basis = holding["shares"] * holding["avg_price"]
    holding["unrealized_pnl"] = holding["current_value"] - cost_basis
    if cost_basis:
        holding["unrealized_pnl_pct"] = round(
            holding["unrealized_pnl"] / cost_basis * 100, 2
        )

    recalculate_summary(portfolio)
    save_portfolio(owner, portfolio)
    return msg


def show_summary() -> str:
    lines = ["📊 포트폴리오 현황\n"]
    for owner, label in [("user", "아내"), ("husband", "남편")]:
        try:
            p = load_portfolio(owner)
            s = p["summary"]
            # KRW 또는 USD 필드 자동 감지
            if "total_value" in s:
                total = s["total_value"]
                pnl = s.get("unrealized_pnl", 0)
                pnl_pct = s.get("unrealized_pnl_pct", 0)
                sign = "+" if pnl >= 0 else ""
                lines.append(
                    f"👤 {label}: {total:,}원\n"
                    f"   손익 {sign}{pnl:,}원 ({sign}{pnl_pct:.2f}%)"
                )
            else:
                total = s.get("total_value_usd", 0)
                pnl = s.get("unrealized_pnl_usd", 0)
                pnl_pct = s.get("unrealized_pnl_pct", 0)
                sign = "+" if pnl >= 0 else ""
                lines.append(
                    f"👤 {label}: ${total:,.2f}\n"
                    f"   손익 {sign}${pnl:,.2f} ({sign}{pnl_pct:.2f}%)"
                )
        except Exception as e:
            lines.append(f"👤 {label}: 조회 실패 ({e})")
    return "\n".join(lines)


def parse_args(args: List[str]) -> Tuple:
    """(owner, name, qty_delta, avg_price) 파싱."""
    owner = "user"
    if args and args[0].lower() in ("husband", "남편", "h"):
        owner = "husband"
        args = args[1:]
    elif args and args[0].lower() in ("user", "나", "아내", "u"):
        args = args[1:]

    if not args:
        raise ValueError("종목명이 없습니다.")

    # 종목명: 숫자/+/-/@ 로 시작하지 않는 토큰들
    name_parts = []
    rest = args[:]
    for i, a in enumerate(args):
        stripped = a.lstrip("+-@").replace(",", "")
        if stripped.replace(".", "").isdigit():
            rest = args[i:]
            break
        name_parts.append(a)
        rest = args[i + 1 :]

    if not name_parts:
        raise ValueError("종목명이 없습니다.")
    name = " ".join(name_parts)

    qty_delta = None
    avg_price = None
    for token in rest:
        token = token.replace(",", "")
        if token.startswith("@"):
            avg_price = float(token[1:])
        elif qty_delta is None:
            qty_delta = int(token.lstrip("+"))

    if qty_delta is None:
        raise ValueError("수량이 없습니다. (+100 또는 -30 형태로 입력)")

    return owner, name, qty_delta, avg_price


USAGE = """사용법: /stock [user|남편] 종목명 [+|-]수량 [@평단가]

예시:
  /stock TIGER반도체 +100 @23000      ← 아내 매수
  /stock 남편 KODEX200 +50 @45000     ← 남편 매수
  /stock TIGER반도체 -30              ← 아내 매도
  /stock                              ← 현황 조회"""


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        print(show_summary())
        sys.exit(0)

    try:
        owner, name, qty_delta, avg_price = parse_args(args)
        print(update_holding(owner, name, qty_delta, avg_price))
    except ValueError as e:
        print(f"❌ {e}\n\n{USAGE}")
        sys.exit(1)
