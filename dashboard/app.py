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


def load_history_df() -> pd.DataFrame:
    """history.json → 부부 합산 DataFrame (월별 등간격 x 좌표 포함)"""
    path = ROOT / "history.json"
    if not path.exists():
        return pd.DataFrame()
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    df_u = (pd.DataFrame([r for r in raw if r.get("note") == "Users"])
              [["date", "total_value", "total_cost", "unrealized_pnl_pct"]]
              .rename(columns={"total_value": "user_value", "total_cost": "user_cost",
                               "unrealized_pnl_pct": "user_pct"}))
    df_h = (pd.DataFrame([r for r in raw if r.get("note") == "Husband"])
              [["date", "total_value", "total_cost", "unrealized_pnl_pct"]]
              .rename(columns={"total_value": "husb_value", "total_cost": "husb_cost",
                               "unrealized_pnl_pct": "husb_pct"}))
    df = (pd.merge(df_u, df_h, on="date", how="outer")
            .sort_values("date").reset_index(drop=True))
    for col in ["user_value", "husb_value", "user_cost", "husb_cost", "user_pct", "husb_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # 합산은 양쪽 모두 데이터가 있는 날만 계산
    df["total_value"] = df[["user_value", "husb_value"]].sum(axis=1, min_count=2)
    df["total_cost"]  = df[["user_cost",  "husb_cost" ]].sum(axis=1, min_count=2)
    df["total_pct"]   = (df["total_value"] - df["total_cost"]) / df["total_cost"] * 100
    return df


_BASE_DATE = pd.Timestamp("2024-12-01")


def to_mx(date_str: str) -> int:
    """날짜 → 기준일로부터의 일수. 하루 = 1칸 등간격."""
    return (pd.Timestamp(date_str) - _BASE_DATE).days


def month_ticks(dates: list) -> tuple:
    """날짜 목록 → 월 시작점 tick values & labels (일별 등간격 기준)"""
    d0 = pd.Timestamp(min(dates)).replace(day=1)
    d1 = pd.Timestamp(max(dates)) + pd.offsets.MonthBegin(1)
    months = pd.date_range(d0, d1, freq="MS")
    vals   = [(m - _BASE_DATE).days for m in months]
    labels = [m.strftime("%y.%m") for m in months]
    return vals, labels


# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="부부 포트폴리오 대시보드",
    page_icon="📈",
    layout="wide",
)

st.title("📈 부부 포트폴리오 대시보드")

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
    col1.metric("부부 총 자산", fmt_krw(summary.get("family_total_krw", 0)))
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

    # 섹터별 비중 파이 차트
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

    # ── history.json 기반 추이 차트 (월별 등간격) ──────────
    df_hist = load_history_df()
    if not df_hist.empty:
        df_hist["mx"] = df_hist["date"].apply(to_mx)
        tvs, tls = month_ticks(df_hist["date"].tolist())
        xax = dict(tickvals=tvs, ticktext=tls, showgrid=True, gridcolor="#eeeeee")
        _layout = dict(legend=dict(orientation="h"), margin=dict(l=0, r=0, t=28, b=0))

        # ① 자산 추이
        df_tot  = df_hist.dropna(subset=["total_value"])
        df_user = df_hist.dropna(subset=["user_value"])
        df_husb = df_hist.dropna(subset=["husb_value"])

        with col_right:
            st.subheader("자산 추이")
            fig_asset = go.Figure()
            fig_asset.add_trace(go.Scatter(
                x=df_tot["mx"],  y=df_tot["total_value"],
                mode="lines+markers", name="부부 합산",
                line=dict(color="#FF4B4B", width=2),
            ))
            fig_asset.add_trace(go.Scatter(
                x=df_user["mx"], y=df_user["user_value"],
                mode="lines+markers", name="나",
                line=dict(color="#4B7BFF", width=1.5, dash="dot"),
            ))
            fig_asset.add_trace(go.Scatter(
                x=df_husb["mx"], y=df_husb["husb_value"],
                mode="lines+markers", name="남편",
                line=dict(color="#4BFF9A", width=1.5, dash="dot"),
            ))
            fig_asset.update_layout(xaxis=xax,
                yaxis=dict(tickformat=",", ticksuffix="원"), **_layout)
            st.plotly_chart(fig_asset, use_container_width=True)

        # ② 투입금 vs 평가금  /  ③ 수익률 추이
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("투입금 vs 평가금")
            df_cv = df_hist.dropna(subset=["total_value", "total_cost"])
            fig_cv = go.Figure()
            fig_cv.add_trace(go.Scatter(
                x=df_cv["mx"], y=df_cv["total_value"],
                mode="lines+markers", name="평가금",
                line=dict(color="#FF4B4B", width=2),
            ))
            fig_cv.add_trace(go.Scatter(
                x=df_cv["mx"], y=df_cv["total_cost"],
                mode="lines+markers", name="투입금",
                line=dict(color="#888888", width=2, dash="dash"),
            ))
            fig_cv.update_layout(xaxis=xax,
                yaxis=dict(tickformat=",", ticksuffix="원"), **_layout)
            st.plotly_chart(fig_cv, use_container_width=True)

        with col_b:
            st.subheader("수익률 추이")
            fig_pct = go.Figure()
            fig_pct.add_trace(go.Scatter(
                x=df_tot["mx"],  y=df_tot["total_pct"],
                mode="lines+markers", name="부부 합산",
                line=dict(color="#FF4B4B", width=2),
            ))
            fig_pct.add_trace(go.Scatter(
                x=df_user["mx"], y=df_user["user_pct"],
                mode="lines+markers", name="나",
                line=dict(color="#4B7BFF", width=1.5, dash="dot"),
            ))
            fig_pct.add_trace(go.Scatter(
                x=df_husb["mx"], y=df_husb["husb_pct"],
                mode="lines+markers", name="남편",
                line=dict(color="#4BFF9A", width=1.5, dash="dot"),
            ))
            fig_pct.add_hline(y=0, line_dash="solid", line_color="#cccccc")
            fig_pct.update_layout(xaxis=xax,
                yaxis=dict(ticksuffix="%"), **_layout)
            st.plotly_chart(fig_pct, use_container_width=True)


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

    # ── 남편 자산 추이 (history.json) ──────────────────────
    st.divider()
    st.subheader("남편 자산 추이")
    path_hist = ROOT / "history.json"
    if path_hist.exists():
        with open(path_hist, encoding="utf-8") as _f:
            _raw = json.load(_f)
        _df_h = (pd.DataFrame([r for r in _raw if r.get("note") == "Husband"])
                   [["date", "total_value", "total_cost", "unrealized_pnl_pct"]]
                   .sort_values("date").reset_index(drop=True))
        _df_h["mx"] = _df_h["date"].apply(to_mx)
        _tvs, _tls = month_ticks(_df_h["date"].tolist())
        _xax = dict(tickvals=_tvs, ticktext=_tls, showgrid=True, gridcolor="#eeeeee")

        col_ha, col_hb = st.columns(2)
        with col_ha:
            st.caption("평가금 vs 투입금")
            fig_hcv = go.Figure()
            fig_hcv.add_trace(go.Scatter(
                x=_df_h["mx"], y=_df_h["total_value"],
                mode="lines+markers", name="평가금",
                line=dict(color="#4BFF9A", width=2),
                text=_df_h["date"], hovertemplate="%{text}<br>%{y:,.0f}원<extra></extra>",
            ))
            fig_hcv.add_trace(go.Scatter(
                x=_df_h["mx"], y=_df_h["total_cost"],
                mode="lines+markers", name="투입금",
                line=dict(color="#888888", width=2, dash="dash"),
                text=_df_h["date"], hovertemplate="%{text}<br>%{y:,.0f}원<extra></extra>",
            ))
            fig_hcv.update_layout(
                xaxis=_xax,
                yaxis=dict(tickformat=",", ticksuffix="원"),
                legend=dict(orientation="h"), margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_hcv, use_container_width=True)

        with col_hb:
            st.caption("수익률 추이")
            fig_hpct = go.Figure()
            fig_hpct.add_trace(go.Scatter(
                x=_df_h["mx"], y=_df_h["unrealized_pnl_pct"],
                mode="lines+markers", name="수익률",
                line=dict(color="#4BFF9A", width=2),
                text=_df_h["date"], hovertemplate="%{text}<br>%{y:.2f}%<extra></extra>",
            ))
            fig_hpct.add_hline(y=0, line_dash="solid", line_color="#cccccc")
            fig_hpct.update_layout(
                xaxis=_xax,
                yaxis=dict(ticksuffix="%"),
                legend=dict(orientation="h"), margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_hpct, use_container_width=True)
