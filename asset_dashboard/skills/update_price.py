#!/usr/bin/env python3
"""
Portfolio Price Updater — Method A
portfolio.json / portfolio_husband.json 의 'ticker' 필드에 야후파이낸스 심볼을 직접 저장.
사용법: python3 skills/update_price.py [--dry-run]
"""

import json
import sys
import warnings
warnings.filterwarnings('ignore')
import yfinance as yf

# ticker 필드에 KRX코드가 없는 경우를 위한 fallback 매핑
# Method A로 점진적 전환 중 — ticker 필드에 직접 코드가 있으면 우선 사용됨
TICKER_MAP = {
    # ACE
    # ACE (한국투자)
    "ACE원자력TOP10": "433500.KS",       # 'ACE 원자력테마딥서치'로 대체 매핑
    "ACEAI반도체TOP10": "441540.KS",     # 'ACE 글로벌반도체TOP10'으로 대체 매핑
    "ACEAI반도체TOP3+": "469150.KS",
    "ACEAI반도체TOP3플러스": "469150.KS",  # ticker 필드 변형 대응
    "ACE코스닥150": "354500.KS",         # 정상 코드 반영 (기존 오기입 수정)
    "ACE테슬라밸류체인액티브": "457480.KS", # 정상 코드 반영 (기존 오기입 수정)

    # KODEX (삼성)
    "KODEX200": "069500.KS",
    "KODEX레버리지": "122630.KS",
    "KODEX미국AI테크TOP10": "485540.KS",       # 'KODEX 미국AI테크TOP10' 코드 반영
    "KODEX미국S&P500": "379800.KS",       # 'KODEX 미국S&P500TR'
    "KODEX미국반도체": "390390.KS",       # 'KODEX 미국반도체MV' 코드 반영
    "KODEX반도체": "091160.KS",
    "KODEX반도체레버리지": "494310.KS",   # KODEX에는 반도체 레버리지가 없어 일반 반도체로 임시 연결
    "KODEX에너지화학": "117460.KS",
    "KODEX증권": "102970.KS",
    "KODEX코스닥150": "229200.KS",
    "KODEX코스닥150레버리지": "233740.KS",
    "KODEX한국대만IT프리미어": "298770.KS", # 'KODEX 한국대만IT프리미어' 코드 반영

    # HANARO (NH아문디)
    "HANARO반도체핵심공정주도주": "476260.KS",   # 'HANARO 반도체핵심공정주도주' 코드 반영

    # TIGER (미래에셋)
    "TIGER반도체TOP10": "396500.KS",     # 정상 코드 반영 (기존 오기입 수정)
    "TIGER반도체TOP10레버리지": "488080.KS", # 정상 코드 반영
    "TIGER미국테크TOP10레버리지": "423920.KS",# 'TIGER 미국나스닥100레버리지'로 임시 연결
    "TIGER미국테크TOP10INDXX": "381170.KS",
    "TIGER미국나스닥100": "133690.KS",
    "TIGER미국S&P500": "360750.KS",
    "TIGER미국배당다우존스": "458730.KS",
    "TIGERK방산&우주": "463250.KS",
    "TIGERK방산우주": "463250.KS",          # ticker 필드 변형 대응
    "TIGER코리아AI전력기기TOP3플러스": "0117V0.KS",
    "TIGER코리아원자력": "0091P0.KS",    
    "TIGER현대차그룹플러스": "138540.KS",
    "TIGER일본니케이225": "241180.KS",

    # SOL (신한)
    "SOL미국원자력SMR": "0051G0.KS",
    "SOL미국원자력": "0051G0.KS",           # ticker 필드 변형 대응
    "SOL미국S&P500": "433330.KS",       # 정상 코드 반영
    "SOL조선TOP3플러스": "466920.KS",     # 정상 코드 반영 (기존 오기입 수정)
    "SOL조선기자재": "0141S0.KS",        

    # RISE (KB - 구 KBSTAR)
    "RISE글로벌원자력": "442320.KS",      # 정상 반영 (사용자 기입본이 맞음)
    "RISE삼성전자SK하이닉스채권혼합50": "0162Z0.KS",
    "RISE삼성전자SK하이닉스": "0162Z0.KS",  # ticker 필드 변형 대응

    # TIME / PLUS / 1Q 등
    "TIME미국나스닥100액티브": "426030.KS",
    "TIME코스닥액티브": "0162Y0.KS",      # 유효한 코드(TIME 코스닥150액티브)로 변경
    "PLUS고배당주채권혼합": "251600.KS",   # 정상 코드 반영 (기존 오기입 수정)
    "1Q200액티브": "451060.KS",

    # 한국 개별주
    "삼성전자": "005930.KS",
    "현대제철": "004020.KS",
    "현대차우": "005385.KS",
    "현대차2우B": "005387.KS",
    "두산에너빌리티": "034020.KS",
    "토모큐브": "475960.KQ",              # 최근 상장 코드(475960)로 수정
    "대한조선": "439260.KS",            
}

# 매도 완료 — 가격 업데이트에서 영구 제외
BLACKLIST = {"엔케이젠바이오텍코리아", "엔케이젠바이오", "182400.KQ"}

# USD 심볼 목록 (가격 × 환율 변환 대상)
USD_TICKERS = {
    "AMZN","ARM","AVGO","GOOGL","IONQ","KORU","NVDA","NVDL",
    "OXY","PLTR","RGTI","RKLB","SOXL","SPCE","TSLA","USO","VRT","GRT",
    "TE","TEL",
}

def get_usd_krw():
    try:
        return yf.Ticker("KRW=X").fast_info['last_price']
    except:
        return 1450.0

def get_price(ticker):
    """(가격, is_usd) 반환. 조회 실패 시 (None, False)"""
    # ticker 필드에 직접 코드 있으면 우선, 없으면 TICKER_MAP fallback
    symbol = ticker if (ticker.endswith('.KS') or ticker.endswith('.KQ') or ticker in USD_TICKERS) \
             else TICKER_MAP.get(ticker, ticker)
    is_usd = symbol in USD_TICKERS
    try:
        price = yf.Ticker(symbol).fast_info['last_price']
        if price and price > 0:
            return price, is_usd
    except:
        pass
    return None, is_usd

def update_portfolio(filepath, dry_run=False, usd_krw=1450.0):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = []
    skipped = []

    for acc in data.get('accounts', []):
        for h in acc.get('holdings', []):
            ticker = h.get('ticker', '').strip()
            if not ticker:
                skipped.append(h['name'])
                continue

            if h.get('name', '') in BLACKLIST or ticker in BLACKLIST:
                continue

            price, is_usd = get_price(ticker)

            if price is None:
                skipped.append(f"{h['name']} ({ticker})")
                continue

            shares    = h.get('shares', 0)
            avg_price = h.get('avg_price', 0)
            price_krw = price * usd_krw if is_usd else price

            old_val  = h.get('current_value', 0)
            new_val  = round(shares * price_krw)
            cost     = shares * avg_price
            new_pnl  = round(new_val - cost)
            new_pct  = round((new_pnl / cost) * 100, 2) if cost > 0 else 0

            results.append({
                'name':    h['name'],
                'old':     old_val,
                'new':     new_val,
                'diff':    new_val - old_val,
                'pnl_pct': new_pct,
            })

            if not dry_run:
                h['current_price']      = round(price_krw)
                h['current_value']      = new_val
                h['unrealized_pnl']     = new_pnl
                h['unrealized_pnl_pct'] = new_pct

    if not dry_run and results:
        # 계좌별 summary 재계산
        for acc in data.get('accounts', []):
            hlist    = acc.get('holdings', [])
            acc_val  = sum(h.get('current_value', 0) for h in hlist)
            acc_cost = sum(h.get('shares', 0) * h.get('avg_price', 0) for h in hlist)
            acc_pnl  = acc_val - acc_cost
            s = acc.setdefault('summary', {})
            s['total_value']         = acc_val
            s['unrealized_pnl']      = acc_pnl
            s['unrealized_pnl_pct']  = round(acc_pnl / acc_cost * 100, 2) if acc_cost > 0 else 0

        # 전체 summary 재계산 (total_value는 건드리지 않음 — 익절 포함 사용자 수정값)
        all_holdings = [h for acc in data['accounts'] for h in acc.get('holdings', [])]
        total_cost = sum(h.get('shares', 0) * h.get('avg_price', 0) for h in all_holdings)
        total_val  = sum(h.get('current_value', 0) for h in all_holdings)
        total_pnl  = total_val - total_cost
        data['summary']['unrealized_pnl']     = round(total_pnl)
        data['summary']['unrealized_pnl_pct'] = round(total_pnl / total_cost * 100, 2) if total_cost > 0 else 0

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return results, skipped


def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print(f"  포트폴리오 현재가 업데이트 {'[DRY RUN — 파일 수정 없음]' if dry_run else '[실제 적용]'}")
    print("=" * 60)

    print("USD/KRW 환율 조회 중...")
    usd_krw = get_usd_krw()
    print(f"  → 1 USD = {usd_krw:,.1f} KRW\n")

    files = [
        '/Users/macmini/myClaude/asset_dashboard/portfolio.json',
        '/Users/macmini/myClaude/asset_dashboard/portfolio_husband.json',
    ]

    for filepath in files:
        fname = filepath.split('/')[-1]
        print(f"▶ {fname}")
        try:
            results, skipped = update_portfolio(filepath, dry_run=dry_run, usd_krw=usd_krw)
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            continue

        # 변동폭 상위 5개 출력
        results.sort(key=lambda x: abs(x['diff']), reverse=True)
        for r in results[:5]:
            sign = '+' if r['diff'] >= 0 else ''
            print(f"  {r['name'][:20]:<20} {sign}{r['diff']:>10,.0f}원  ({r['pnl_pct']:+.1f}%)")

        if skipped:
            print(f"\n  ⚠ 가격 조회 실패 ({len(skipped)}개) — ticker 필드에 KRX코드 입력 필요:")
            for s in skipped:
                print(f"    - {s}")

        print(f"\n  ✅ {len(results)}종목 업데이트{'(미적용)' if dry_run else ' 완료'}\n")

    # 섹터 스냅샷 저장
    from datetime import date
    save_sector_snapshot(files, str(date.today()), dry_run=dry_run)


SECTOR_MAP_PY = {
    '반도체':        ['반도체','반도체(해외)','반도체(미국)','반도체/레버리지','반도체ETF/레버리지(해외)','AI/반도체(해외)'],
    'AI/기술':       ['AI/기술','AI/기술(해외)','AI/기술(미국)','기술(해외)','IT/기술','해외기술','해외기술/레버리지'],
    '원자력/에너지': ['원자력','원자력/에너지','원자력/에너지(국내)','원자력/에너지(미국)','에너지/화학','에너지(해외)','설비투자'],
    '방산/우주':     ['방산/우주','방산/우주(미국)','방위/전략','우주/방산(해외)'],
    '조선':          ['조선'],
    '시장지수':      ['시장지수','시장지수(미국)','시장지수(일본)','레버리지/지수','해외지수'],
    '그룹주/자동차': ['그룹주','자동차','로봇/자동차'],
    '바이오':        ['바이오'],
    '금융':          ['금융','금융(미국)'],
    '기타':          ['양자컴퓨팅(해외)','전기차/기술(해외)','혼합/채권','철강','화학','기타','기타(미국)','기타(국내)'],
}

def save_sector_snapshot(files, today, dry_run=False):
    """두 포트폴리오의 섹터별 합산을 sector_history.json에 저장"""
    totals = {}
    for fpath in files:
        try:
            with open(fpath) as f:
                data = json.load(f)
        except:
            continue
        for acc in data.get('accounts', []):
            for h in acc.get('holdings', []):
                cat = h.get('category', '기타')
                sector = next((s for s, cats in SECTOR_MAP_PY.items() if cat in cats), '기타')
                totals[sector] = totals.get(sector, 0) + (h.get('current_value') or 0)

    snapshot = {
        'date': today,
        'sectors': {k: round(v) for k, v in sorted(totals.items(), key=lambda x: -x[1])},
        'total': round(sum(totals.values()))
    }

    hist_path = '/Users/macmini/myClaude/asset_dashboard/sector_history.json'
    try:
        with open(hist_path) as f:
            hist = json.load(f)
    except:
        hist = []

    # 같은 날짜 있으면 덮어쓰기, 없으면 추가
    hist = [e for e in hist if e['date'] != today]
    hist.append(snapshot)
    hist.sort(key=lambda x: x['date'])

    if not dry_run:
        with open(hist_path, 'w', encoding='utf-8') as f:
            json.dump(hist, f, indent=2, ensure_ascii=False)

    top3 = list(snapshot['sectors'].items())[:3]
    print(f"  📊 섹터 스냅샷 저장 {'(미적용)' if dry_run else '완료'}: {today}")
    for s, v in top3:
        pct = v / snapshot['total'] * 100 if snapshot['total'] else 0
        print(f"     {s}: {v/1e8:.2f}억 ({pct:.1f}%)")


if __name__ == '__main__':
    main()
