#!/usr/bin/env python3
"""Unifero tools module - Web search and documentation crawling toolkit.

Contains the UniferoTool class which exposes process_request for programmatic use.
Features enhanced networking with retries, improved HTML parsing for code extraction,
and robust error handling.
"""
from typing import Optional, List, Dict, Any, Tuple
import logging
import re
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# HTTP headers for requests
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; unifero-cli/1.0)"}

# Request timeout settings
DEFAULT_TIMEOUT = 10
SEARCH_TIMEOUT = 15


def _build_session(timeout: int = 10) -> requests.Session:
    """Create a requests.Session with a retry strategy.

    Returns a session that retries on common transient errors.
    """
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(HEADERS)
    return session


def normalize_url(href: str, base: Optional[str] = None) -> Optional[str]:
    """Normalize hrefs found on pages to absolute URLs when possible.

    Handles common redirect wrappers (e.g. DuckDuckGo uddg) and protocol-relative
    URLs. Returns None for javascript and fragment links.
    """
    if not href:
        return None

    href = href.strip()
    # ignore javascript and fragments
    if href.startswith("javascript:") or href.startswith("#"):
        return None

    parsed = urlparse(href)

    # handle DuckDuckGo redirect wrappers like /l/?uddg=<url>
    if parsed.query and "uddg=" in parsed.query:
        qs = parse_qs(parsed.query)
        uddg_vals = qs.get("uddg")
        if uddg_vals:
            target = uddg_vals[0]
            return target

    if href.startswith("//"):
        return "https:" + href

    if parsed.scheme in ("http", "https"):
        return href

    if base:
        return urljoin(base, href)

    return None


def safe_get(session: requests.Session, url: str, timeout: int = DEFAULT_TIMEOUT) -> Optional[requests.Response]:
    """Perform a GET request using the provided session and return the response or None."""
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code != 200:
            logger.debug("safe_get: non-200 status %s for %s", resp.status_code, url)
            return None
        return resp
    except requests.exceptions.RequestException as e:
        logger.debug("safe_get exception for %s: %s", url, e)
        return None
    except Exception as e:
        logger.warning("Unexpected error in safe_get for %s: %s", url, e)
        return None


def extract_html_title_and_paragraphs(resp: requests.Response) -> Tuple[Optional[str], List[str], Optional[str], Optional[str]]:
    """Parse HTML response and extract title, paragraphs, favicon and og:image.

    Returns (title, paragraphs, favicon, og_image). favicon and og_image will be
    normalized to absolute URLs when possible using resp.url as the base.
    """
    soup = BeautifulSoup(resp.text, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else None

    # Extract favicon: look for link rel containing 'icon'
    favicon = None
    for link in soup.find_all("link", href=True):
        rel = link.get("rel")
        if not rel:
            continue
        # rel can be a list or string
        rels = [r.lower() for r in rel] if isinstance(rel, (list, tuple)) else [rel.lower()]
        if any("icon" in r for r in rels):
            href = link.get("href")
            favicon = normalize_url(href, base=resp.url)
            if favicon:
                break

    # Extract Open Graph image (preview)
    og_image = None
    og_tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if og_tag and og_tag.get("content"):
        og_image = normalize_url(og_tag.get("content"), base=resp.url)
    else:
        # Fallback: twitter:image
        tw_tag = soup.find("meta", property="twitter:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if tw_tag and tw_tag.get("content"):
            og_image = normalize_url(tw_tag.get("content"), base=resp.url)

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "svg", "noscript"]):
        tag.decompose()

    paragraphs: List[str] = []
    
    # Enhanced extraction: Handle code blocks and preserve formatting
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "code", "blockquote"]):
        # Handle code blocks with special formatting
        if tag.name in ["pre", "code"]:
            code_text = tag.get_text(separator="\n", strip=False)
            if code_text.strip() and len(code_text.strip()) >= 10:  # Only include substantial code
                # Mark as code block for better identification
                formatted_code = f"```\n{code_text.strip()}\n```"
                paragraphs.append(formatted_code)
        else:
            text = tag.get_text(" ", strip=True)
            if not text:
                continue
            # Reduce minimum length for headers and important elements
            min_length = 10 if tag.name.startswith('h') else 20
            if len(text) < min_length:
                continue
            paragraphs.append(text)
    
    # Also extract any remaining code that might be in other elements
    for code_tag in soup.find_all("code"):
        if code_tag.parent and code_tag.parent.name != "pre":  # Avoid duplicates from pre>code
            code_text = code_tag.get_text(strip=True)
            if code_text and len(code_text) >= 20 and code_text not in [p.replace('```\n', '').replace('\n```', '') for p in paragraphs]:
                paragraphs.append(f"`{code_text}`")
    
    return title, paragraphs, favicon, og_image


def extract_doc_content_html(url: str, length: Optional[int] = 2000, session: Optional[requests.Session] = None) -> Optional[Dict[str, Any]]:
    """Backward-compatible extractor: call with (url, length) or (url, length, session).

    If session is not provided, a session will be created internally.
    """
    if session is None:
        session = _build_session()
    resp = safe_get(session, url)
    if not resp:
        return None

    title, paragraphs, favicon, og_image = extract_html_title_and_paragraphs(resp)

    content_lines: List[str] = []
    for p in paragraphs:
        if re.match(r"^[A-Z][A-Za-z0-9\-\s]{2,}$", p) and len(p.split()) <= 6:
            content_lines.append(f"\n## {p}\n")
        else:
            content_lines.append(p)

    text = "\n\n".join(content_lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if length is None:
        return {"title": title or "", "paragraphs": paragraphs, "content": text, "favicon": favicon, "og_image": og_image}
    return {"title": title or "", "paragraphs": paragraphs, "content": text[:length], "favicon": favicon, "og_image": og_image}


def duckduckgo_search(query: str, limit: int = 10, session: Optional[requests.Session] = None) -> List[str]:
    """Search DuckDuckGo and return a list of result URLs.

    Backward-compatible signature: duckduckgo_search(query, limit) or duckduckgo_search(query, limit, session=...)
    """
    if session is None:
        session = _build_session()
    q = query.replace(" ", "+")
    url = f"https://duckduckgo.com/html/?q={q}"
    try:
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            logger.debug("duckduckgo_search: non-200 status %s for %s", resp.status_code, url)
            return []
    except Exception as e:
        logger.debug("duckduckgo_search exception for %s: %s", url, e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links: List[str] = []
    seen = set()

    for a in soup.select("a.result__a, a.result-link"):
        href = a.get("href")
        final = normalize_url(href)
        if final and final not in seen:
            seen.add(final)
            links.append(final)
        if len(links) >= limit:
            return links

    for a in soup.find_all("a", href=True):
        if len(links) >= limit:
            break
        href = a["href"]
        final = normalize_url(href)
        if final and final not in seen:
            seen.add(final)
            links.append(final)

    return links[:limit]


def deep_search(query: str, limit: int = 5, snippet_len: int = 300, content_len: Optional[int] = 2000) -> Dict[str, Any]:
    # call duckduckgo_search without passing a session to preserve backward
    # compatibility for callers/tests that monkeypatch the function.
    links = duckduckgo_search(query, limit=limit)
    results: List[Dict[str, Any]] = []

    for link in links:
        logger.info("Extracting: %s", link)
        # keep compatibility with monkeypatched extractors by not forcing a session
        extracted = extract_doc_content_html(link, length=content_len)
        if not extracted:
            results.append({"url": link, "title": None, "snippet": None, "content": None})
            continue
        title = extracted.get("title") or ""
        paragraphs = extracted.get("paragraphs") or []
        favicon = extracted.get("favicon")
        og_image = extracted.get("og_image")
        snippet = None
        if paragraphs:
            snippet = paragraphs[0][:snippet_len]
        else:
            content_text = extracted.get("content", "")
            snippet = (content_text[:snippet_len] + "...") if len(content_text) > snippet_len else content_text

        results.append({
            "url": link,
            "title": title,
            "snippet": snippet,
            "content": extracted.get("content"),
            "favicon": favicon,
            "og_image": og_image,
        })

    return {"query": query, "results": results}


def crawl_docs(base_url: str, limit: int = 50) -> List[str]:
    session = _build_session()
    visited = set()
    to_visit = [base_url]
    domain = urlparse(base_url).netloc
    docs_links = set()

    logger.info("Starting crawl: %s", base_url)

    while to_visit and len(docs_links) < limit:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = session.get(url, timeout=10)
            if resp is None or resp.status_code != 200:
                continue
            ctype = resp.headers.get("Content-Type", "")
            if "text/html" not in ctype:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                link = normalize_url(a["href"], base=url)
                if not link:
                    continue
                if urlparse(link).netloc == domain and "/doc" in link:
                    if link not in visited and len(docs_links) < limit:
                        docs_links.add(link)
                        to_visit.append(link)
        except Exception as e:
            logger.debug("Skipping %s: %s", url, e)
            continue

    logger.info("Found %s doc links.", len(docs_links))
    return sorted(docs_links)


def fetch_docs_data(base_url: str, limit: int = 10, include_content: bool = True, content_limit: Optional[int] = 2000) -> Dict[str, Any]:
    data: List[Dict[str, Any]] = []
    if limit is None:
        limit = 10
    limit = int(limit)
    if limit > 10:
        limit = 10

    links = crawl_docs(base_url, limit=limit)
    links = links[:limit]
    
    # If crawl found no doc links, include the base_url itself so
    # callers get at least one meaningful result when include_content is true.
    # But FIRST try to fetch the exact URL provided
    if not links:
        links = [base_url]
    else:
        # Always include the exact base_url as the first result for better accuracy
        if base_url not in links:
            links = [base_url] + links[:limit-1]
    
    session = _build_session()
    for i, link in enumerate(links, start=1):
        logger.info("(%s/%s) Processing: %s", i, len(links), link)
        item: Dict[str, Any] = {"url": link}
        if include_content:
            # call without session to stay compatible with simple monkeypatches
            extracted = extract_doc_content_html(link, length=content_limit)
            if not extracted:
                # Extraction failed (network/non-200/etc). Provide explicit flags
                item["title"] = None
                item["content"] = None
                item["favicon"] = None
                item["og_image"] = None
                item["fetched"] = False
                item["error"] = "failed to fetch or parse"
            else:
                item["title"] = extracted.get("title")
                item["content"] = extracted.get("content")
                item["favicon"] = extracted.get("favicon")
                item["og_image"] = extracted.get("og_image")
                item["fetched"] = True
        data.append(item)
    return {"base_url": base_url, "results": data}


class UniferoTool:
    """High-level tool wrapper for the unifero toolset."""

    def process_request(self, params: dict) -> dict:
        mode = params.get("mode", "search")

        if mode == "search":
            query = params.get("query")
            if not query:
                raise ValueError("'query' is required for search mode")
            limit = int(params.get("limit", 5))
            snippet_len = int(params.get("snippet_len", 300))
            content_len = params.get("content_len", 2000)
            if content_len is not None:
                content_len = int(content_len)
            return deep_search(query, limit=limit, snippet_len=snippet_len, content_len=content_len)

        elif mode == "docs":
            url = params.get("url")
            if not url:
                raise ValueError("'url' is required for docs mode")
            limit = int(params.get("limit", 10))
            if limit > 10:
                limit = 10
            include_content = bool(params.get("include_content", True))
            content_limit = params.get("content_limit", None)
            if content_limit is not None:
                content_limit = int(content_limit)
            return fetch_docs_data(url, limit=limit, include_content=include_content, content_limit=content_limit)

        else:
            raise ValueError("Invalid mode. Use 'search' or 'docs'.")
