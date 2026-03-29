"""
네이버 로그인 + 쿠키 저장 모듈
- 최초 실행 시 로그인 후 cookies.json 저장
- 이후 실행 시 쿠키 재사용 (만료 시 재로그인)
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, BrowserContext

load_dotenv(Path(__file__).parent / ".env")

NAVER_ID = os.getenv("NAVER_ID")
NAVER_PW = os.getenv("NAVER_PW")
COOKIES_PATH = Path(__file__).parent / "cookies.json"
LOGIN_URL = "https://nid.naver.com/nidlogin.login"
CHECK_URL = "https://www.naver.com"


def save_cookies(context: BrowserContext):
    cookies = context.cookies()
    COOKIES_PATH.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))


def load_cookies(context: BrowserContext) -> bool:
    if not COOKIES_PATH.exists():
        return False
    cookies = json.loads(COOKIES_PATH.read_text())
    context.add_cookies(cookies)
    return True


def is_logged_in(page: Page) -> bool:
    page.goto(CHECK_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    if "nidlogin" in page.url:
        return False
    # 로그인 상태면 네이버 메인에 아이디가 쿠키에 존재
    cookies = page.context.cookies()
    nid_cookies = [c for c in cookies if c["name"] in ("NID_AUT", "NID_SES")]
    return len(nid_cookies) >= 2


def do_login(page: Page):
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1000)

    # ID 입력
    page.locator("#id").click()
    page.keyboard.type(NAVER_ID, delay=80)
    page.wait_for_timeout(500)

    # PW 입력 (보안 키패드 우회: JS로 직접 값 세팅)
    page.evaluate("""(pw) => {
        const el = document.querySelector('#pw');
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(el, pw);
        el.dispatchEvent(new Event('input', { bubbles: true }));
    }""", NAVER_PW)
    page.wait_for_timeout(500)

    # 로그인 버튼 클릭
    page.locator("#log\\.login").click()
    page.wait_for_timeout(3000)


def get_logged_in_context(playwright, headless=True):
    """로그인된 브라우저 컨텍스트 반환."""
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    # 저장된 쿠키로 시도
    if load_cookies(context):
        if is_logged_in(page):
            print("✅ 쿠키로 로그인 성공")
            return browser, context, page

    # 재로그인
    print("🔐 로그인 시도 중...")
    do_login(page)

    # 로그인 직후 naver.com에 있으면 성공으로 간주
    if "naver.com" in page.url and "nidlogin" not in page.url:
        save_cookies(context)
        print("✅ 로그인 성공, 쿠키 저장됨")
    else:
        current = page.url
        print(f"⚠️  로그인 실패 또는 추가 인증 필요. 현재 URL: {current}")

    return browser, context, page


if __name__ == "__main__":
    with sync_playwright() as p:
        browser, context, page = get_logged_in_context(p, headless=False)
        print("현재 URL:", page.url)
        input("브라우저 확인 후 Enter...")
        browser.close()
