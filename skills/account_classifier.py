"""
Skill 1: Account Classifier
스크린샷 또는 텍스트를 분석하여 User / Husband 계좌를 자동 분류하고
해당 portfolio JSON에 데이터를 저장합니다.
"""

import base64
import json
import re
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

USER_PORTFOLIO = DATA_DIR / "portfolio_user.json"
HUSBAND_PORTFOLIO = DATA_DIR / "portfolio_husband.json"

# 계좌 식별 힌트 (계좌번호 prefix, 앱 이름 등)
OWNER_HINTS = {
    "user": [
        "43707842",       # 기존 확인된 계좌번호
        "연금저축",
        "ISA",
        "미래에셋",
    ],
    "husband": [
        "남편",
        "husband",
        "키움",
        "삼성증권",
    ],
}


def classify_owner_from_text(text: str) -> str:
    """텍스트에서 소유자를 판별합니다."""
    text_lower = text.lower()
    for hint in OWNER_HINTS["husband"]:
        if hint.lower() in text_lower:
            return "husband"
    for hint in OWNER_HINTS["user"]:
        if hint.lower() in text_lower:
            return "user"
    return "unknown"


def classify_owner_with_claude(image_path: str | None = None, text: str | None = None) -> dict:
    """Claude Vision API로 이미지/텍스트를 분석하여 소유자와 보유 종목을 추출합니다."""
    client = anthropic.Anthropic()

    content = []

    if image_path:
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        ext = Path(image_path).suffix.lower().lstrip(".")
        media_type = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": image_data},
        })

    prompt_text = """이 스크린샷 또는 텍스트는 주식 계좌 현황입니다.

다음 정보를 JSON으로 추출하세요:
1. owner: 이 계좌가 "user"(아내)인지 "husband"(남편)인지 판별
   - 계좌번호 43707842로 시작하면 "user"
   - 남편/husband 언급 또는 다른 증권사면 "husband"
   - 판단 불가시 "unknown"

2. account: { id, name, currency("KRW" or "USD"), last_updated(YYYY-MM-DD) }

3. summary: { total_value, total_cost, unrealized_pnl, unrealized_pnl_pct, cash }
   (USD 계좌면 필드명에 _usd 붙이기)

4. holdings: 보유 종목 배열
   각 항목: { name, ticker, shares, avg_price, current_price, current_value,
               unrealized_pnl, unrealized_pnl_pct, type("ETF"/"STOCK"), category }

반드시 유효한 JSON만 응답하세요. 마크다운 코드블록 없이 JSON만."""

    if text:
        prompt_text = f"다음 텍스트 데이터:\n{text}\n\n" + prompt_text

    content.append({"type": "text", "text": prompt_text})

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()
    # JSON 블록 추출
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        raise ValueError(f"JSON을 파싱할 수 없습니다: {raw[:200]}")
    return json.loads(json_match.group())


def save_to_portfolio(data: dict) -> Path:
    """분류된 데이터를 해당 소유자의 portfolio JSON에 저장합니다."""
    owner = data.get("owner", "unknown")

    if owner == "user":
        target = USER_PORTFOLIO
    elif owner == "husband":
        target = HUSBAND_PORTFOLIO
    else:
        print(f"⚠️  소유자를 판별할 수 없습니다. 수동으로 지정해 주세요.")
        choice = input("소유자 입력 (user/husband): ").strip().lower()
        owner = choice
        data["owner"] = owner
        target = USER_PORTFOLIO if owner == "user" else HUSBAND_PORTFOLIO

    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ [{owner.upper()}] 포트폴리오 저장 완료: {target}")
    return target


def run(image_path: str | None = None, text: str | None = None):
    """메인 실행 함수."""
    if not image_path and not text:
        print("사용법: python account_classifier.py [이미지경로] [텍스트]")
        sys.exit(1)

    print("🔍 계좌 분류 중...")

    # 텍스트만 있을 때 간단히 힌트로 먼저 분류 시도
    if text and not image_path:
        quick_owner = classify_owner_from_text(text)
        if quick_owner != "unknown":
            print(f"📝 텍스트 힌트로 소유자 식별: {quick_owner}")

    data = classify_owner_with_claude(image_path=image_path, text=text)
    print(f"👤 소유자: {data.get('owner', 'unknown')}")
    print(f"💼 종목 수: {len(data.get('holdings', []))}")

    saved_path = save_to_portfolio(data)
    return saved_path


if __name__ == "__main__":
    img = sys.argv[1] if len(sys.argv) > 1 else None
    txt = sys.argv[2] if len(sys.argv) > 2 else None
    run(image_path=img, text=txt)
