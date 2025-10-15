import pytest

from tools.unifero import UniferoTool


def test_search_mode_monkeypatched(monkeypatch):
    # Mock duckduckgo_search and extract_doc_content_html in tools.unifero
    def fake_duckduckgo_search(query, limit=10):
        return ["https://example.com/page1", "https://example.com/page2"]

    def fake_extract(url, length=2000):
        return {"title": f"Title for {url}", "paragraphs": ["This is a paragraph about the page."], "content": "full content"}

    monkeypatch.setattr('tools.unifero.duckduckgo_search', fake_duckduckgo_search)
    monkeypatch.setattr('tools.unifero.extract_doc_content_html', fake_extract)

    tool = UniferoTool()
    params = {"mode": "search", "query": "test query", "limit": 2, "snippet_len": 50, "content_len": 100}
    out = tool.process_request(params)

    assert out['query'] == 'test query'
    assert len(out['results']) == 2
    assert out['results'][0]['url'] == 'https://example.com/page1'
    assert 'title' in out['results'][0]


def test_docs_mode_monkeypatched(monkeypatch):
    # Mock crawl_docs and extract_doc_content_html in tools.unifero
    def fake_crawl(base_url, limit=50):
        # return more than allowed to ensure limit enforced
        return [f"{base_url}/doc{i}" for i in range(1, 15)]

    def fake_extract(url, length=2000):
        return {"title": f"T {url}", "paragraphs": ["para"], "content": "X"}

    monkeypatch.setattr('tools.unifero.crawl_docs', fake_crawl)
    monkeypatch.setattr('tools.unifero.extract_doc_content_html', fake_extract)

    tool = UniferoTool()
    params = {"mode": "docs", "url": "https://example.com/docs", "limit": 20, "include_content": True}
    out = tool.process_request(params)

    # limit should be capped to 10 by process_request
    assert len(out['results']) <= 10
    for item in out['results']:
        assert 'url' in item
        assert 'title' in item
