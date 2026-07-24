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


def crawl_website(url: str) -> dict:
    response = requests.get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "Chrome/120 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=20,
    )


    if response.status_code == 403:
        raise RuntimeError(
            f"""
    Website blocked crawler:

    {url}

    Reason:
    The website uses anti-bot protection.

    Solutions:
    1. Use a browser crawler (Playwright)
    2. Use website sitemap/API
    3. Use another test website
    """
        )
    
    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
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

    cta_texts = []

    for tag in soup.find_all(
        [
            "a",
            "button",
        ]
    ):
        text = tag.get_text(strip=True)

        if len(text) > 2:
            cta_texts.append(text)

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
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "headings": list(dict.fromkeys(headings)),
        "paragraphs": list(dict.fromkeys(paragraphs)),
        "cta_texts": list(dict.fromkeys(cta_texts)),
        "image_alt_texts": list(dict.fromkeys(image_alt_texts)),
        "iframe_links": iframe_links,
    }


def run(module_input: dict) -> dict:
    """
    Always crawl.
    Cache management is handled only by main.py.
    """

    data = crawl_website(module_input["website_url"])

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