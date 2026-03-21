"""
Skill 3: 3-Tab Dashboard (Streamlit)
가족 포트폴리오를 3개 탭으로 시각화합니다.
실행: streamlit run dashboard/app.py
"""

import json
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fmt_krw(val: float) -> str:
    if abs(val) >= 1_0000_0000:
        return f"{val/1_0000_0000:.2f}억원"
    elif abs(val) >= 10000:
        return f"{val/10000:.0f}만원"
    return f"{val:,.0f}원"


def pnl_color(val: float) -> str:
    return "red" if val > 0 else "blue"


# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="가족 포트폴리오 대시보드",
    page_icon="📈",
    layout="wide",
)

st.title("📈 가족 포트폴리오 대시보드")

total = load_json(DATA_DIR / "portfolio_total.json")
user = load_json(DATA_DIR / "portfolio_user.json")
husband = load_json(DATA_DIR / "portfolio_husband.json")

if not total and not user:
    st.warning("데이터가 없습니다. `skills/aggregator.py`를 먼저 실행해 주세요.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["🏠 Total Family", "👩 My Portfolio", "👨 Husband's Portfolio"])


# ── TAB 1: Total Family ──────────────────────────────────
with tab1:
    summary = total.get("summary", {})
    last_updated = total.get("last_updated", "N/A")
    fx = total.get("fx_rate_usd_krw", 1450)

    st.caption(f"마지막 업데이트: {last_updated}  |  USD/KRW: {fx:,.0f}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("가족 총 자산", fmt_krw(summary.get("family_total_krw", 0)))
    col2.metric(
        "총 평가손익",
        fmt_krw(summary.get("family_pnl_krw", 0)),
        f"{summary.get('family_pnl_pct', 0):+.2f}%",
    )
    col3.metric(
        "전월 대비 (MoM)",
        fmt_krw(summary.get("mom_krw", 0)),
        f"{summary.get('mom_pct', 0):+.2f}%",
    )
    col4.metric("나의 자산", fmt_krw(summary.get("user_total_krw", 0)))

    st.divider()
    col_left, col_right = st.columns(2)

    # 카테고리 파이 차트
    cats = total.get("category_breakdown_krw", {})
    if cats:
        with col_left:
            st.subheader("섹터별 비중")
            fig_pie = px.pie(
                names=list(cats.keys()),
                values=list(cats.values()),
                hole=0.35,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

    # 월별 자산 추이
    history = total.get("monthly_history", [])
    if len(history) >= 2:
        with col_right:
            st.subheader("월별 총 자산 추이")
            df_hist = pd.DataFrame(history)
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=df_hist["date"], y=df_hist["total_value_krw"],
                mode="lines+markers", name="총 자산",
                line=dict(color="#FF4B4B", width=2),
            ))
            fig_line.add_trace(go.Scatter(
                x=df_hist["date"], y=df_hist["user_value_krw"],
                mode="lines+markers", name="나의 자산",
                line=dict(color="#4B7BFF", width=2, dash="dot"),
            ))
            fig_line.add_trace(go.Scatter(
                x=df_hist["date"], y=df_hist["husband_value_krw"],
                mode="lines+markers", name="남편 자산",
                line=dict(color="#4BFF9A", width=2, dash="dot"),
            ))
            fig_line.update_layout(
                yaxis_tickformat=",",
                legend=dict(orientation="h"),
                margin=dict(l=0, r=0, t=20, b=0),
            )
            st.plotly_chart(fig_line, use_container_width=True)
    elif history:
        st.info("월별 추이 차트는 2개월 이상의 데이터가 필요합니다.")


# ── TAB 2: My Portfolio ──────────────────────────────────
def render_portfolio_tab(portfolio: dict, owner_label: str):
    if not portfolio or not portfolio.get("holdings"):
        st.info(f"{owner_label} 포트폴리오 데이터가 없습니다.")
        return

    summary = portfolio.get("summary", {})
    account = portfolio.get("account", {})
    currency = account.get("currency", "KRW")

    col1, col2, col3 = st.columns(3)
    total_val = summary.get("total_value") or summary.get("total_value_usd", 0)
    pnl = summary.get("unrealized_pnl") or summary.get("unrealized_pnl_usd", 0)
    pnl_pct = summary.get("unrealized_pnl_pct", 0)

    label_suffix = f" ({currency})" if currency == "USD" else ""
    col1.metric(f"평가금액{label_suffix}", f"{total_val:,.0f}")
    col2.metric("평가손익", f"{pnl:+,.0f}", f"{pnl_pct:+.2f}%")
    col3.metric("계좌명", account.get("name", "-"))

    st.divider()

    holdings = portfolio.get("holdings", [])
    df = pd.DataFrame(holdings)

    if df.empty:
        st.info("보유 종목이 없습니다.")
        return

    col_left, col_right = st.columns(2)

    # 수익률 바 차트
    with col_left:
        st.subheader("수익률 순위")
        df_sorted = df.sort_values("unrealized_pnl_pct", ascending=True)
        colors = ["#FF4B4B" if x > 0 else "#4B7BFF" for x in df_sorted["unrealized_pnl_pct"]]
        fig_bar = go.Figure(go.Bar(
            x=df_sorted["unrealized_pnl_pct"],
            y=df_sorted["name"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.1f}%" for v in df_sorted["unrealized_pnl_pct"]],
            textposition="outside",
        ))
        fig_bar.update_layout(
            xaxis_title="수익률 (%)",
            margin=dict(l=0, r=60, t=10, b=0),
            height=max(300, len(df) * 32),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # 카테고리 파이
    with col_right:
        st.subheader("카테고리 비중")
        cat_group = df.groupby("category")["current_value"].sum().reset_index()
        fig_pie = px.pie(
            cat_group,
            names="category",
            values="current_value",
            hole=0.35,
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    # 종목 테이블
    st.subheader("보유 종목 상세")
    display_cols = ["name", "shares", "avg_price", "current_price", "current_value",
                    "unrealized_pnl", "unrealized_pnl_pct", "category"]
    display_cols = [c for c in display_cols if c in df.columns]
    df_display = df[display_cols].copy()
    df_display.columns = ["종목명", "수량", "평균단가", "현재가", "평가금액",
                           "평가손익", "수익률(%)", "카테고리"][:len(display_cols)]

    st.dataframe(
        df_display.style.format({
            "수량": "{:,.0f}",
            "평균단가": "{:,.0f}",
            "현재가": "{:,.0f}",
            "평가금액": "{:,.0f}",
            "평가손익": "{:+,.0f}",
            "수익률(%)": "{:+.2f}%",
        }).background_gradient(subset=["수익률(%)"], cmap="RdYlGn"),
        use_container_width=True,
        hide_index=True,
    )


with tab2:
    render_portfolio_tab(user, "나의")

with tab3:
    render_portfolio_tab(husband, "남편")
