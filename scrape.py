import re
import asyncio
import os
from bs4 import BeautifulSoup
from collections import deque
from markdownify import markdownify
from crawl4ai import AsyncWebCrawler
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
import shutil

br = "-" * 100
max_depth = 1
dir = "./markdown"


def delete_md_files(dir="./markdown"):
    for root, dirs, files in os.walk(dir):
        for f in files:
            pth = os.path.join(root, f)
            if pth.endswith(".md"):
                os.remove(pth)
                print(f"Deleted {f}.")
    print(f"{dir} directory cleared")


def clean_text(text: str) -> str:
    """Clean crawled markdown text into plain readable text."""
    # 1. Remove image markdown like ![](url)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # 2. Replace markdown links [text](url) → keep text only
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # 3. Remove bare URLs (http/https/www)
    text = re.sub(r"http[s]?://\S+|www\.\S+", "", text)
    # 4. Remove dangling empty () or []
    text = re.sub(r"\(\s*\)|\[\s*\]", "", text)
    # 5. Remove lines with only special chars (*, #, spaces)
    text = re.sub(r"^[\s*#]+$", "", text, flags=re.MULTILINE)
    text = re.sub("^!\[\].*\n", "", text)
    # 6. Collapse repeated sections (optional deduplication)
    lines = text.splitlines()
    seen = set()
    deduped = []
    for line in lines:
        line_stripped = line.strip()
        if (line_stripped and line_stripped not in seen) or len(line_stripped) < 2:
            deduped.append(line)
            seen.add(line_stripped)
    text = "\n".join(deduped)
    # 7. Normalize whitespace
    text = re.sub(r"\n\s*\n+", "\n\n", text)  # collapse multiple blank lines
    text = re.sub(r" {2,}", " ", text)  # collapse multiple spaces
    return text.strip()


def get_filename(url, dir="."):
    f = url
    f = f.replace("\s", "_")
    f = f.replace("https://", "")
    f = f.replace("/", "-")
    f = f.replace(".com", "")
    f = f.replace(".inc", "")
    f = f.replace(".", "_")
    f = f.replace("www", "")
    return f"./{dir}/{f}_content.md"


def save_file(md, url, dir="./generated"):
    file = get_filename(url, dir)
    with open(file, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Saved {url} md to {file}")


def append_md_to_file(md, file, url, dir):
    if not file:
        file = get_filename(url, dir)
    with open(file, "a", encoding="utf-8") as f:
        f.write(f"{md}\n{br}\n")


def clear_file(filename):
    with open(filename, "w") as f:
        f.write("")
    print(f"Cleared file: {filename}")


async def crawl(cur_url):
    """Fetch markdown content for a single URL using crawl4ai."""
    try:
        print(f"Crawl: Extracting content from {cur_url}")
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(cur_url)
            if not result or not result.markdown:
                raise ValueError("No markdown found")
            md = clean_text(result.markdown)
            return md, result.html
    except Exception as e:
        return e


async def playwright(cur_url):
    """Fetch markdown content for a single URL using playwright."""
    try:
        print(f"Playwright: Extracting content from {cur_url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(cur_url, timeout=30000)
            html = await page.content()
            md = markdownify(html)
            md = clean_text(md)
            await browser.close()
            return md, html
    except Exception as e:
        raise e


async def scrape(url, dir):
    print("Called scrape")
    visited = set()
    q = deque()
    q.append((url, 0))
    max_depth = 2  # or use the appropriate value
    chunks = set()
    dir = dir
    text = ""
    file = get_filename(url, dir)
    while q:
        cur_url, depth = q.pop()
        if cur_url in visited or depth > max_depth:
            continue
        visited.add(cur_url)

        try:
            print(f"Trying crawl for {cur_url}")
            md, html = await crawl(cur_url)
        except Exception as e:
            print(f"Crawl failed for {cur_url}: {e}")
            try:
                print(f"Trying playwright for {cur_url}")
                md, html = await playwright(cur_url)
            except Exception as e2:
                print(f"Playwright failed for {cur_url}: {e2}")
                continue  # skip this URL

        if md not in chunks:
            chunks.add(md)
            text += f"{md}\n"
            append_md_to_file(md, file, None, dir)
        # Extract links for next level
        if depth < max_depth:
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                abs_url = urljoin(cur_url, href)
                if urlparse(abs_url).netloc == urlparse(url).netloc:
                    if abs_url not in visited:
                        q.append((abs_url, depth + 1))

    print(f"Extracted markdown saved to {file}.")
    return text


async def main():
    pass


if __name__ == "__main__":
    asyncio.run(main())
