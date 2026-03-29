# Skill: Update Portfolio Prices (실시간 주가 및 수익률 업데이트)

## Description
사용자가 "현재가로 업데이트해줘"라고 요청할 때 실행되는 스킬입니다.
`portfolio.json` 계열의 파일들을 읽어오거나 거기에 없다면, finance.naver.com에 가서 검색하여 각 주식/ETF의 실시간 현재가(`current_price`)를 불러오고, 이에 따라 평가금액(`current_value`)과 미실현 수익/수익률(`unrealized_pnl`, `unrealized_pnl_pct`)을 자동 재계산하여 파일을 업데이트합니다.

## Execution Steps
1. 업데이트 대상 JSON 파일(`portfolio_user.json`, `portfolio_husband.json`, `portfolio_total.json` 등)을 로드합니다.
2. 각 자산 항목의 `ticker` 또는 `name`을 확인하여 표준 종목 코드(예: 233740.KS)로 변환합니다.
3. 외부 API(예: yfinance)를 호출하여 실시간 `current_price`를 가져옵니다. 혹여 값이 없다면 기존 값을 그대로 두고 업데이트 못한 목록들을 알려줍니다. 
4. 아래의 공식을 사용하여 나머지 값을 재계산합니다:
   - `총 매수금액` = `shares` * `avg_price`
   - `current_value` = `shares` * `current_price`
   - `unrealized_pnl` = `current_value` - `총 매수금액`
   - `unrealized_pnl_pct` = (`unrealized_pnl` / `총 매수금액`) * 100 (소수점 둘째 자리까지 반올림)
5. 업데이트된 데이터로 기존 JSON 파일을 덮어씁니다.
6. 업데이트 완료 후, 변동폭이 컸던 종목이나 전체 자산의 변화를 사용자에게 간략히 브리핑합니다.

## Python Tool (Action)
AI는 아래의 파이썬 스크립트 구조를 활용하여 데이터를 업데이트합니다.

```python
import json
import yfinance as yf

# 한글 ETF/주식 이름을 야후 파이낸스 티커로 변환하는 맵핑 딕셔너리 (필요시 추가)
TICKER_MAP = {
    "KODEX코스닥150레버리지": "233740.KS",
    "테슬라": "TSLA",
    "애플": "AAPL"
    # 추가 종목들 매핑...
}

def get_realtime_price(ticker_name):
    # 매핑된 티커가 있으면 사용하고, 없으면 그대로 사용
    symbol = TICKER_MAP.get(ticker_name, ticker_name)
    try:
        stock = yf.Ticker(symbol)
        price = stock.fast_info['last_price']
        return price
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None

def update_portfolio_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            portfolio = json.load(f)
            
        updated = False
        
        # 포트폴리오 내 자산 리스트 순회 (키 이름은 실제 JSON 구조에 맞게 조정: 예 'assets' 또는 최상위 리스트)
        for asset in portfolio: # 만약 dict 구조라면 portfolio['assets'] 등으로 접근
            ticker_name = asset.get("ticker", asset.get("name"))
            current_price = get_realtime_price(ticker_name)
            
            if current_price:
                shares = asset["shares"]
                avg_price = asset["avg_price"]
                
                # 계산 로직
                total_cost = shares * avg_price
                new_current_value = shares * current_price
                new_unrealized_pnl = new_current_value - total_cost
                new_unrealized_pnl_pct = (new_unrealized_pnl / total_cost) * 100 if total_cost > 0 else 0
                
                # 값 업데이트 (소수점 처리)
                asset["current_price"] = round(current_price, 2)
                asset["current_value"] = round(new_current_value, 2)
                asset["unrealized_pnl"] = round(new_unrealized_pnl, 2)
                asset["unrealized_pnl_pct"] = round(new_unrealized_pnl_pct, 2)
                
                updated = True
                
        if updated:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(portfolio, f, indent=2, ensure_ascii=False)
            print(f"[{filepath}] 실시간 가격 및 수익률 업데이트가 완료되었습니다.")
            
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {filepath}")

# 실행 예시
# update_portfolio_json('data/portfolio_user.json')