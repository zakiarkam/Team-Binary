"""
Website crawler — extracts visible marketing-relevant content.

This stage supports intelligent caching.

Flow

input.json
      │
      ▼
SHA256(input)
      │
      ▼
same?
 ┌────┴────┐
 │         │
Yes       No
 │         │
 ▼         ▼
Load     Crawl
Cache    Website
 │         │
 └────┬────┘
      ▼
Save metadata
"""

import json

import requests
from bs4 import BeautifulSoup

import config
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

session = requests.Session()
retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[
        429,
        500,
        502,
        503,
        504,
    ],
    allowed_methods=frozenset(["GET"]),
)

session.mount(
    "https://",
    HTTPAdapter(max_retries=retry),
)

session.mount(
    "http://",
    HTTPAdapter(max_retries=retry),
)

USER_AGENT = (
    "Mozilla/5.0 "
    "(Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)

def extract_page_data(html: str) -> dict:
    """
    Extract all marketing-related information from HTML.
    """

    soup = BeautifulSoup(
        html,
        "lxml",
    )

    title = (
        soup.title.get_text(strip=True)
        if soup.title
        else ""
    )

    meta_tag = soup.find(
        "meta",
        attrs={
            "name": "description",
        },
    )

    meta_description = (
        meta_tag.get("content", "")
        if meta_tag
        else ""
    )

    headings = [
        h.get_text(strip=True)
        for h in soup.find_all(
            [
                "h1",
                "h2",
                "h3",
            ]
        )
        if h.get_text(strip=True)
    ]

    paragraphs = [
        p.get_text(strip=True)
        for p in soup.find_all("p")
        if p.get_text(strip=True)
    ]

    cta_texts = [
        tag.get_text(strip=True)
        for tag in soup.find_all(
            [
                "a",
                "button",
            ]
        )
        if len(tag.get_text(strip=True)) > 2
    ]

    image_alt_texts = [
        image.get("alt", "").strip()
        for image in soup.find_all("img")
        if image.get("alt", "").strip()
    ]

    iframe_links = [
        iframe.get("src")
        for iframe in soup.find_all("iframe")
        if iframe.get("src")
    ]

    return {
        "title": title,
        "meta_description": meta_description,
        "headings": list(dict.fromkeys(headings)),
        "paragraphs": list(dict.fromkeys(paragraphs)),
        "cta_texts": list(dict.fromkeys(cta_texts)),
        "image_alt_texts": list(dict.fromkeys(image_alt_texts)),
        "iframe_links": iframe_links,
    }

def crawl_playwright(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True
        )
        try:
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="en-US",
                viewport={
                    "width": 1440,
                    "height": 900,
                },
            )

            page = context.new_page()

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            if response is None:
                raise RuntimeError("No response from Playwright.")

            if response.status >= 400:
                raise RuntimeError(
                    f"HTTP {response.status}"
                )
            
            try:
                page.wait_for_load_state(
                    "networkidle",
                    timeout=10000,
                )

            except PlaywrightTimeoutError:
                pass

            html = page.content()

            if len(html) < 500:
                raise RuntimeError(
                    "Playwright returned unusually small page."
                )

            return html
                
        finally:
            if "context" in locals():
                context.close()
            browser.close()


def crawl_website(url: str) -> dict:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,"
            "application/xhtml+xml,"
            "application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

    try:
        response = session.get(
            url,
            headers=headers,
            timeout=20,
            allow_redirects=True,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        if "text/html" not in content_type:
            raise RuntimeError(
                f"Expected HTML but got {content_type}"
            )

        # requests falls back to ISO-8859-1 for text/html when the HTTP header
        # carries no charset (RFC 2616), ignoring the page's own
        # <meta charset>. That silently turns every em-dash and accented
        # character into mojibake — and this text becomes marketing copy, so
        # the damage would be visible to the customer. Prefer the encoding the
        # bytes actually indicate.
        if "charset=" not in content_type:
            response.encoding = response.apparent_encoding or "utf-8"

        html = response.text

        if len(html.strip()) < 500:
            raise RuntimeError(
                "Received unusually small HTML document."
            )

        lower_html = html.lower()

        blocked_markers = [
            "access denied",
            "checking your browser",
            "cf-browser-verification",
            "cf-challenge",
            "captcha",
            "verify you are human",
            "please enable cookies",
            "just a moment",
            "security check",
        ]

        if any(marker in lower_html for marker in blocked_markers):
            raise requests.exceptions.RequestException(
                "Browser challenge detected."
            )

    except (
        requests.exceptions.RequestException,
        RuntimeError,
    ) as request_error:
        print(
            "[crawler] Requests failed:",
            request_error,
        )

        try:
            print("[crawler] Falling back to Playwright...")

            html = crawl_playwright(url)

        except Exception as playwright_error:

            return {
                "url": url,
                "status": "failed",
                "error": {
                    "requests_error": str(request_error),
                    "playwright_error": str(playwright_error),
                },
                "title": "",
                "meta_description": "",
                "headings": [],
                "paragraphs": [],
                "cta_texts": [],
                "image_alt_texts": [],
                "iframe_links": [],
            }

    page_data = extract_page_data(html)

    content_score = (
        len(" ".join(page_data["paragraphs"]))
        +
        len(" ".join(page_data["headings"]))
    )

    if content_score < 3:
        print(
            "[crawler] Empty HTML detected. Retrying with Playwright..."
        )

        html = crawl_playwright(url)

        page_data = extract_page_data(html)

    return {
        "url": url,
        **page_data,
    }


def run(module_input: dict) -> dict:
    """
    Always crawl.
    Cache management is handled only by main.py.
    """

    data = crawl_website(
        module_input["website_url"]
    )


    if data.get("status") == "failed":

        print(
            "[crawler] Website unavailable. "
            "Skipping crawler stage."
        )

        with open(
            config.CRAWL_JSON,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False,
            )

        return data
    with open(
        config.CRAWL_JSON,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False,
        )

    print(
        f"Crawled {data['url']} → "
        f"{len(data['paragraphs'])} paragraphs, "
        f"{len(data['cta_texts'])} CTAs, "
        f"{len(data['headings'])} headings."
    )

    return data

def load_cached() -> dict:
    with open(
        config.CRAWL_JSON,
        encoding="utf-8",
    ) as file:
        return json.load(file)