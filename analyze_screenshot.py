#!/usr/bin/env python3
"""
증권사 앱 스크린샷을 분석하여 portfolio.json을 자동 업데이트하는 스크립트
사용법: python analyze_screenshot.py <이미지_파일_경로>
"""

import argparse
import base64
import json
import os
import sys
from datetime import date
from pathlib import Path

import anthropic


PORTFOLIO_PATH = Path(__file__).parent / "portfolio.json"


def load_portfolio() -> dict:
    """기존 portfolio.json 로드"""
    if PORTFOLIO_PATH.exists():
        with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_portfolio(data: dict):
    """portfolio.json 저장"""
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ portfolio.json 업데이트 완료: {PORTFOLIO_PATH}")


def encode_image(image_path: str) -> tuple[str, str]:
    """이미지를 base64로 인코딩하고 미디어 타입 반환"""
    path = Path(image_path)
    suffix = path.suffix.lower()

    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }

    media_type = media_type_map.get(suffix, "image/jpeg")

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    return image_data, media_type


def analyze_screenshot(image_path: str) -> dict:
    """Claude API로 스크린샷 분석"""
    client = anthropic.Anthropic()

    print(f"\n📸 이미지 분석 중: {image_path}")

    image_data, media_type = encode_image(image_path)

    prompt = """이 증권사 앱 스크린샷을 분석하여 포트폴리오 데이터를 JSON 형식으로 추출해주세요.

다음 형식의 JSON만 반환해주세요 (다른 텍스트 없이):

{
  "account": {
    "name": "계좌명 또는 null",
    "currency": "KRW 또는 USD"
  },
  "summary": {
    "total_value": 총평가금액(숫자),
    "total_cost": 총매입금액(숫자),
    "unrealized_pnl": 평가손익(숫자),
    "unrealized_pnl_pct": 수익률(숫자, % 제외),
    "cash": 예수금(숫자, 없으면 0)
  },
  "holdings": [
    {
      "name": "종목명",
      "ticker": "티커 또는 종목코드",
      "shares": 보유수량(숫자),
      "avg_price": 평균단가(숫자),
      "current_price": 현재가(숫자, 없으면 null),
      "current_value": 평가금액(숫자),
      "unrealized_pnl": 평가손익(숫자),
      "unrealized_pnl_pct": 수익률(숫자, % 제외),
      "type": "ETF 또는 STOCK",
      "category": "섹터 분류 (예: 반도체, 원자력, 방산, 조선 등)"
    }
  ]
}

주의사항:
- 숫자에서 쉼표(,)나 통화 기호(₩, $)는 제거하고 순수 숫자만
- 보이지 않는 항목은 null로 처리
- 수익률은 % 기호 제외한 숫자만 (예: 27.66)
- JSON 이외의 텍스트나 마크다운 코드블록 없이 순수 JSON만 반환"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # 코드블록이 있으면 제거
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    try:
        extracted_data = json.loads(response_text)
        print("✅ 스크린샷 분석 성공!")
        return extracted_data
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        print(f"원본 응답:\n{response_text}")
        sys.exit(1)


def merge_portfolio(existing: dict, new_data: dict) -> dict:
    """기존 포트폴리오와 새 데이터 병합 (스크린샷 데이터 우선)"""
    today = date.today().isoformat()

    merged = existing.copy() if existing else {}

    # account 업데이트
    if "account" not in merged:
        merged["account"] = {}

    if new_data.get("account", {}).get("name"):
        merged["account"]["name"] = new_data["account"]["name"]
    merged["account"]["currency"] = new_data.get("account", {}).get("currency", "KRW")
    merged["account"]["last_updated"] = today

    # summary 업데이트 (스크린샷 우선)
    if "summary" in new_data:
        merged["summary"] = new_data["summary"]

    # holdings 업데이트 (스크린샷 우선)
    if "holdings" in new_data and new_data["holdings"]:
        merged["holdings"] = new_data["holdings"]
        print(f"\n📊 {len(new_data['holdings'])}개 종목 감지됨")

    return merged


def print_summary(data: dict):
    """분석 결과 요약 출력"""
    print("\n" + "=" * 50)
    print("📈 포트폴리오 현황 요약")
    print("=" * 50)

    if "account" in data:
        print(f"계좌: {data['account'].get('name', 'N/A')}")
        print(f"통화: {data['account'].get('currency', 'N/A')}")

    if "summary" in data:
        s = data["summary"]
        currency = "₩" if data.get("account", {}).get("currency") == "KRW" else "$"
        total = s.get("total_value", 0) or 0
        pnl = s.get("unrealized_pnl", 0) or 0
        pnl_pct = s.get("unrealized_pnl_pct", 0) or 0

        print(f"\n총 평가금액: {currency}{total:,.0f}")
        print(f"평가 손익:   {currency}{pnl:,.0f} ({pnl_pct:+.2f}%)")

    if "holdings" in data:
        print(f"\n보유 종목 수: {len(data['holdings'])}개")
        print("\n[종목 목록]")
        for h in data["holdings"]:
            pnl_pct = h.get("unrealized_pnl_pct", 0) or 0
            arrow = "▲" if pnl_pct >= 0 else "▼"
            print(f"  {arrow} {h['name']}: {h['shares']}주, 평단 {h['avg_price']:,}원, 수익률 {pnl_pct:+.2f}%")

    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="증권사 앱 스크린샷을 분석하여 portfolio.json 업데이트"
    )
    parser.add_argument("image", help="분석할 스크린샷 이미지 파일 경로")
    parser.add_argument(
        "--no-save", action="store_true", help="portfolio.json 저장하지 않고 분석만"
    )
    args = parser.parse_args()

    # API 키 확인
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ 오류: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   export ANTHROPIC_API_KEY='your-api-key'")
        sys.exit(1)

    # 이미지 파일 확인
    if not Path(args.image).exists():
        print(f"❌ 오류: 이미지 파일을 찾을 수 없습니다: {args.image}")
        sys.exit(1)

    # 스크린샷 분석
    new_data = analyze_screenshot(args.image)

    # 기존 포트폴리오 로드 및 병합
    existing = load_portfolio()
    merged = merge_portfolio(existing, new_data)

    # 요약 출력
    print_summary(merged)

    # 저장
    if not args.no_save:
        save_portfolio(merged)
    else:
        print("\n(--no-save 옵션으로 저장 건너뜀)")


if __name__ == "__main__":
    main()
