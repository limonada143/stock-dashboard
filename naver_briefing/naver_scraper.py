"""
네이버 블로그 + 프리미엄콘텐츠 최신 글 수집
- 블로그: PostTitleListAsync API → 오늘/어제 글만 필터
- 프리미엄: 지정 URL에서 HTML 파싱
"""

import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from urllib.parse import unquote_plus

from dotenv import load_dotenv
from pathlib import Path
from playwright.sync_api import sync_playwright, Page
from naver_login import get_logged_in_context

load_dotenv(Path(__file__).parent / ".env")

# ── 설정 ──────────────────────────────────────────────────
BLOG_IDS = ["tosoha1", "ranto28", "pokara61", "khiro38", "hodolry", "sungdory"]
PREMIUM_URL = "https://contents.premium.naver.com/butterdaddy/butterdaddy123/authors/19a8bb42a4ezo5"
POSTS_PER_BLOG = 5  # 최근 N개 가져와서 날짜 필터

YOUTUBE_CHANNELS = [
    {"id": "@orlandocampus", "name": "올랜도킴"},
]


def fetch_blog_posts(page: Page, blog_id: str, since_days: int = 1) -> list[dict]:
    """블로그 최신 글 API로 수집, since_days일 이내 글만 반환."""
    url = (
        f"https://blog.naver.com/PostTitleListAsync.naver"
        f"?blogId={blog_id}&viewdate=&currentPage=1"
        f"&categoryNo=&parentCategoryNo=&countPerPage={POSTS_PER_BLOG}"
    )
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    try:
        raw = page.locator("body").inner_text()
        # 네이버 API가 잘못된 이스케이프 시퀀스를 포함하는 경우 대비
        data = json.loads(raw)
        posts = data.get("postList", [])
    except json.JSONDecodeError:
        # fallback: regex로 직접 추출
        import re
        log_nos = re.findall(r'"logNo"\s*:\s*"(\d+)"', raw)
        titles_enc = re.findall(r'"title"\s*:\s*"([^"]+)"', raw)
        add_dates = re.findall(r'"addDate"\s*:\s*"([^"]+)"', raw)
        posts = [
            {"logNo": log_nos[i], "title": titles_enc[i],
             "addDate": add_dates[i] if i < len(add_dates) else ""}
            for i in range(len(log_nos))
        ]
    except Exception:
        return []

    cutoff = (datetime.now() - timedelta(days=since_days)).date()
    results = []
    for post in posts:
        try:
            date_str = post.get("addDate", "")  # "2026. 3. 25."
            post_date = datetime.strptime(date_str.strip(), "%Y. %m. %d.").date()
            if post_date < cutoff:
                continue
        except Exception:
            pass  # 날짜 파싱 실패 시 포함

        title = unquote_plus(post.get("title", ""))
        log_no = post.get("logNo", "")
        results.append({
            "source": "blog",
            "blog": blog_id,
            "title": title,
            "date": post.get("addDate", "").strip(),
            "url": f"https://blog.naver.com/{blog_id}/{log_no}",
            "content": "",
        })
    return results


def fetch_blog_content(page: Page, url: str) -> str:
    """블로그 글 본문 텍스트 추출."""
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        # iframe 안에 본문이 있는 경우
        frame = page.frame_locator("#mainFrame")
        if frame:
            text = frame.locator(".se-main-container, #postViewArea").first.inner_text()
            return text[:3000]
    except Exception:
        pass
    return ""


def fetch_premium_posts(page: Page, since_days: int = 1) -> list[dict]:
    """프리미엄콘텐츠 페이지에서 최신 글 수집."""
    page.goto(PREMIUM_URL, wait_until="networkidle")
    page.wait_for_timeout(2000)
    html = page.content()

    titles = re.findall(r'class="content_title">\s*([^\n<]+)', html)
    links = re.findall(r'href="(/butterdaddy/[^"]+/contents/[^"]+)"', html)
    dates = re.findall(r'(\d{4}\.\d{2}\.\d{2}\.)', html)

    cutoff = datetime.now() - timedelta(days=since_days)
    results = []
    used_links = set()

    for i, title in enumerate(titles):
        link = ""
        if i < len(links) and links[i] not in used_links:
            link = "https://contents.premium.naver.com" + links[i]
            used_links.add(links[i])

        date_str = dates[i] if i < len(dates) else ""
        try:
            post_date = datetime.strptime(date_str, "%Y.%m.%d.")
            if post_date < cutoff:
                continue
        except Exception:
            pass

        results.append({
            "source": "premium",
            "blog": "버터대디",
            "title": title.strip(),
            "date": date_str,
            "url": link,
            "content": "",
        })

    return results


def fetch_youtube_latest(channel_id: str, channel_name: str, since_days: int = 1) -> list[dict]:
    """유튜브 채널의 최신 영상 수집 (since_days 이내)."""
    try:
        result = subprocess.run(
            ["python3", "-m", "yt_dlp",
             "--flat-playlist", "--playlist-items", "1:5",
             "--print", "%(id)s|||%(title)s|||%(upload_date)s",
             f"https://www.youtube.com/{channel_id}/videos"],
            capture_output=True, text=True, timeout=30
        )
        articles = []
        cutoff = (datetime.now() - timedelta(days=since_days)).date()
        for line in result.stdout.strip().splitlines():
            parts = line.split("|||")
            if len(parts) < 2:
                continue
            vid_id, title = parts[0].strip(), parts[1].strip()
            upload_date = parts[2].strip() if len(parts) > 2 else ""

            # 날짜 필터 (upload_date = YYYYMMDD or NA)
            if upload_date and upload_date != "NA":
                try:
                    post_date = datetime.strptime(upload_date, "%Y%m%d").date()
                    if post_date < cutoff:
                        continue
                except Exception:
                    pass

            articles.append({
                "source": "youtube",
                "blog": channel_name,
                "title": title,
                "date": upload_date,
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "content": "",
                "video_id": vid_id,
            })
        return articles
    except Exception as e:
        print(f"  ⚠️ 유튜브 수집 오류 ({channel_name}): {e}")
        return []


def summarize_youtube_with_gemini(video_url: str, title: str) -> str:
    """Gemini로 유튜브 영상 요약."""
    try:
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                f"다음 유튜브 영상을 보고 핵심 투자/시황 인사이트를 150자 이내로 한국어로 요약해줘."
                f" 영상 제목: '{title}'\n영상 URL: {video_url}"
            ]
        )
        return response.text.strip()
    except Exception as e:
        return f"(요약 실패: {e})"


def collect_all(since_days: int = 1, fetch_content: bool = False) -> list[dict]:
    """전체 수집 실행."""
    with sync_playwright() as p:
        browser, context, page = get_logged_in_context(p, headless=True)

        all_articles = []

        for blog_id in BLOG_IDS:
            print(f"  📰 {blog_id} 수집 중...")
            posts = fetch_blog_posts(page, blog_id, since_days=since_days)
            if fetch_content:
                for post in posts:
                    post["content"] = fetch_blog_content(page, post["url"])
            all_articles.extend(posts)
            print(f"     → {len(posts)}개")

        print("  💎 버터대디 프리미엄 수집 중...")
        premium = fetch_premium_posts(page, since_days=since_days)
        all_articles.extend(premium)
        print(f"     → {len(premium)}개")

        browser.close()

    # 유튜브 수집 (브라우저 불필요)
    for ch in YOUTUBE_CHANNELS:
        print(f"  📺 {ch['name']} 유튜브 수집 중...")
        yt_posts = fetch_youtube_latest(ch["id"], ch["name"], since_days=since_days)
        # Gemini로 각 영상 요약
        for post in yt_posts:
            post["content"] = summarize_youtube_with_gemini(post["url"], post["title"])
        all_articles.extend(yt_posts)
        print(f"     → {len(yt_posts)}개")

    print(f"\n총 {len(all_articles)}개 수집")
    return all_articles


if __name__ == "__main__":
    articles = collect_all(since_days=1)
    for a in articles:
        print(f"[{a['source']}] {a['blog']} | {a['date']} | {a['title'][:50]}")
