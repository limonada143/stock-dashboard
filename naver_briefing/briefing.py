"""
수집된 글들을 Claude로 요약하고 텔레그램으로 전송
"""

import os
import subprocess
import requests
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CLAUDE_BIN = "/Users/macmini/.nvm/versions/node/v24.14.0/bin/claude"


def summarize_with_claude(articles: list[dict]) -> str:
    """Claude CLI로 전체 글 묶어서 브리핑 요약."""
    if not articles:
        return "오늘 새 글이 없습니다."

    lines = []
    for a in articles:
        src = {"blog": "블로그", "premium": "프리미엄", "youtube": "유튜브"}.get(a["source"], a["source"])
        lines.append(f"[{src}] {a['blog']} - {a['date']}")
        lines.append(f"제목: {a['title']}")
        if a.get("content"):
            lines.append(f"내용: {a['content'][:500]}")
        lines.append("")
    articles_text = "\n".join(lines)

    # 링크 참조 맵 생성
    ref_map = {}
    for a in articles:
        key = a["title"][:20]
        ref_map[key] = a.get("url", "")

    refs_text = "\n".join([f'- {a["blog"]} "{a["title"][:30]}": {a.get("url","")}' for a in articles if a.get("url")])

    prompt = f"""다음은 오늘 구독 중인 네이버 블로그/프리미엄콘텐츠/유튜브 글 목록입니다.
투자자 입장에서 오늘 아침 꼭 알아야 할 내용으로 브리핑해주세요.

작성 지침:
1. **핵심 이슈** — 오늘 가장 중요한 매크로/시장 이슈 1~3개를 먼저 요약
2. **반도체/AI** — 반도체, AI 관련 내용이 있으면 별도로 정리 (NVDA, 메모리, 전력 등)
3. **미국 증시** — 미장 흐름, 트럼프/관세, 연준 관련 내용 정리
4. **국내 증시** - 섹터 관련 이야기
5. **투자 액션 힌트** — 글에서 읽히는 시사점이나 주의할 점 1~2줄. 특히 아래 내 보유 ETF 섹터와 연관된 내용 있으면 꼭 언급해줘 (매수/매도 추천 아닌 참고용)

내 보유 ETF 섹터:
- 반도체: TIGER반도체TOP10, KODEX반도체
- 원자력: ACE원자력TOP10, HANARO원자력iSelect
- 방산/우주: TIGER K방산&우주, TIGER 코리아시전략기기TOP3플러스
- 조선: SOL 조선TOP3플러스, SOL 조선기자재
- 바이오: TIME K바이오액티브
- 해외: TIME 미국나스닥100액티브
- 그룹주: TIGER 삼성그룹, TIGER 현대차그룹플러스
- 기타: KODEX증권, ACE코스닥150, KODEX200

형식:
- 각 섹션은 이모지 + 굵은 제목으로 구분
- 글이 없는 섹션은 생략
- 전체 600자 이내
- 각 내용 끝에 출처를 텔레그램 HTML 하이퍼링크로 표시. 형식: (<a href="URL">출처명 날짜</a>) 예: (<a href="https://...">올랜도킴 3/25</a>)
- 날짜는 월/일 형식으로 (예: 3/25)
- 텔레그램 HTML 형식 사용 (<b>, <i>, <a> 태그만)

출처 목록:
{refs_text}

---
{articles_text}
"""

    result = subprocess.run(
        [CLAUDE_BIN, "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI 오류: {result.stderr}")
    return result.stdout.strip()


def send_telegram(text: str):
    """텔레그램으로 메시지 전송."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    })
    if resp.json().get("ok"):
        print("✅ 텔레그램 전송 완료")
    else:
        print("❌ 전송 실패:", resp.json())


def run_briefing(since_days: int = 1):
    from naver_scraper import collect_all

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n📋 {today} 아침 브리핑 시작")

    articles = collect_all(since_days=since_days)

    if not articles:
        msg = f"📭 {today} — 오늘 새 글이 없습니다."
        send_telegram(msg)
        return

    print("🤖 Claude 요약 중...")
    summary = summarize_with_claude(articles)

    header = f"📰 <b>{today} 아침 브리핑</b> ({len(articles)}개 글)\n\n"
    footer = "\n\n<i>— 냥봇 자동 브리핑</i>"
    message = header + summary + footer

    print("\n" + "="*50)
    print(message)
    print("="*50 + "\n")

    send_telegram(message)


if __name__ == "__main__":
    run_briefing(since_days=1)
