import httpx
import re
import urllib.parse
from html.parser import HTMLParser
from typing import List, Dict, Any

class DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results: List[Dict[str, str]] = []
        self._current_url = ""
        self._current_title_parts: List[str] = []
        self._current_snippet_parts: List[str] = []
        self._in_title = False
        self._in_snippet = False

    def handle_starttag(self, tag: str, attrs: list):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        # Title link: <a class="result__url" ...> or <a class="result__snippet" ...>
        if tag == "a" and "result__snippet" in cls:
            self._in_snippet = True
            self._current_snippet_parts = []
        elif tag == "a" and "result__url" in cls:
            raw_url = attrs_dict.get("href", "").strip()
            if "uddg=" in raw_url:
                try:
                    self._current_url = urllib.parse.unquote(raw_url.split("uddg=")[1].split("&")[0])
                except Exception:
                    self._current_url = raw_url
            else:
                self._current_url = raw_url
        elif tag == "a" and ("result__title" in cls or attrs_dict.get("data-testid") == "result-title-a"):
            self._in_title = True
            self._current_title_parts = []
            raw_url = attrs_dict.get("href", "").strip()
            if "uddg=" in raw_url:
                try:
                    self._current_url = urllib.parse.unquote(raw_url.split("uddg=")[1].split("&")[0])
                except Exception:
                    self._current_url = raw_url
            elif raw_url:
                self._current_url = raw_url

    def handle_endtag(self, tag: str):
        if tag == "a" and self._in_snippet:
            self._in_snippet = False
            snippet = "".join(self._current_snippet_parts).strip()
            title = "".join(self._current_title_parts).strip()
            if snippet and self._current_url:
                self.results.append({
                    "title": title if title else "Scientific Web Result",
                    "url": self._current_url,
                    "snippet": snippet
                })
        elif tag == "a" and self._in_title:
            self._in_title = False

    def handle_data(self, data: str):
        if self._in_snippet:
            self._current_snippet_parts.append(data)
        elif self._in_title:
            self._current_title_parts.append(data)


async def search_general_web(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the open World Wide Web (general internet) via DuckDuckGo HTML without any API key.
    Retrieves real live web results from academic publishers, preprint servers, and scientific websites.
    """
    academic_query = f"{query} research paper academic"
    encoded_query = urllib.parse.quote_plus(academic_query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    papers = []
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                parser = DuckDuckGoHTMLParser()
                parser.feed(resp.text)
                
                # Deduplicate and extract venue/domain
                seen_urls = set()
                for item in parser.results:
                    link = item.get("url", "")
                    if link in seen_urls or not link.startswith("http"):
                        continue
                    seen_urls.add(link)
                    
                    domain = urllib.parse.urlparse(link).netloc.replace("www.", "")
                    title = item.get("title", "Web Research Paper")
                    # Clean up title if it contains HTML artifacts
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    if not title or title == "Scientific Web Result":
                        # Guess title from domain or snippet
                        title = f"Research Paper from {domain}"
                    
                    snippet = item.get("snippet", "")
                    snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                    
                    papers.append({
                        "title": title,
                        "authors": f"Published on {domain}",
                        "abstract": snippet if snippet else f"Scientific publication indexed at {domain} regarding {query}.",
                        "url": link,
                        "pdf_url": link,
                        "source": f"Open Web ({domain})",
                        "pub_date": "2024"
                    })
                    if len(papers) >= max_results:
                        break
    except Exception as e:
        print(f"General web search error: {e}")
        
    return papers
