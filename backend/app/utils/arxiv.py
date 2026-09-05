import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

def _reconstruct_openalex_abstract(inverted_index: Dict[str, List[int]]) -> str:
    """Reconstruct standard abstract text from OpenAlex inverted index structure."""
    if not inverted_index:
        return ""
    word_pos = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_pos.append((pos, word))
    word_pos.sort(key=lambda x: x[0])
    return " ".join([w for _, w in word_pos])

async def search_openalex(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """Search OpenAlex (250M+ scientific papers) for relevant research works with rich metadata."""
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per-page": max_results,
        "sort": "relevance_score:desc"
    }
    headers = {
        "User-Agent": "AutonomousResearchScientistAgent/2.0 (mailto:arsa-research@example.com)"
    }
    papers = []
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                for work in data.get("results", []):
                    title = work.get("title") or "Untitled Paper"
                    authors_list = [
                        a.get("author", {}).get("display_name", "")
                        for a in work.get("authorships", [])
                        if a.get("author", {}).get("display_name")
                    ]
                    authors = ", ".join(authors_list[:4])
                    if len(authors_list) > 4:
                        authors += " et al."
                    abstract = _reconstruct_openalex_abstract(work.get("abstract_inverted_index"))
                    doi_url = work.get("doi") or work.get("id") or ""
                    pdf_url = ""
                    primary_loc = work.get("primary_location") or {}
                    venue = primary_loc.get("source", {}).get("display_name") if isinstance(primary_loc.get("source"), dict) else None
                    if primary_loc.get("pdf_url"):
                        pdf_url = primary_loc.get("pdf_url")
                    elif doi_url:
                        pdf_url = doi_url
                    pub_date = str(work.get("publication_year", ""))
                    
                    source_label = f"Peer-Reviewed ({venue})" if venue else "OpenAlex / Peer-Reviewed"
                    
                    papers.append({
                        "title": title,
                        "authors": authors if authors else "Academic Researchers",
                        "abstract": abstract if abstract else f"Published peer-reviewed work investigating {title}.",
                        "url": doi_url if doi_url else "https://openalex.org",
                        "pdf_url": pdf_url if pdf_url else doi_url,
                        "source": source_label,
                        "pub_date": pub_date
                    })
    except Exception as e:
        print(f"OpenAlex search error: {e}")
    return papers

async def search_arxiv(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """
    Search academic literature across arXiv and OpenAlex.
    Retrieves a rich, diverse set of up to max_results real scientific papers online.
    """
    papers = []
    # 1. Query arXiv for preprints
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": min(max_results, 6),
        "sortBy": "relevance",
        "sortOrder": "descending"
    }
    headers = {
        "User-Agent": "AutonomousResearchScientistAgent/2.0 (mailto:researcher@example.org)"
    }
    
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code == 200 and "<feed" in response.text:
                root = ET.fromstring(response.text)
                ns = {
                    "atom": "http://www.w3.org/2005/Atom",
                    "opensearch": "http://a9.com/-/spec/opensearch/1.1/"
                }
                entries = root.findall("atom:entry", ns)
                for entry in entries:
                    title = entry.find("atom:title", ns)
                    summary = entry.find("atom:summary", ns)
                    published = entry.find("atom:published", ns)
                    paper_id = entry.find("atom:id", ns)
                    
                    title_text = title.text.strip().replace("\n", " ") if title is not None else "Untitled"
                    summary_text = summary.text.strip().replace("\n", " ") if summary is not None else ""
                    pub_date = published.text.strip()[:10] if published is not None and published.text else ""
                    id_url = paper_id.text.strip() if paper_id is not None else ""
                    pdf_url = id_url.replace("abs", "pdf") if "abs" in id_url else id_url
                    
                    authors = []
                    for author in entry.findall("atom:author", ns):
                        name = author.find("atom:name", ns)
                        if name is not None:
                            authors.append(name.text.strip())
                    authors_str = ", ".join(authors[:4])
                    if len(authors) > 4:
                        authors_str += " et al."
                    
                    papers.append({
                        "title": title_text,
                        "authors": authors_str if authors_str else "arXiv Researchers",
                        "abstract": summary_text,
                        "url": id_url,
                        "pdf_url": pdf_url,
                        "source": "arXiv Preprint",
                        "pub_date": pub_date
                    })
    except Exception as e:
        print(f"arXiv query skipped or rate-limited: {e}")
        
    # 2. Complement with OpenAlex peer-reviewed journal papers
    needed = max_results - len(papers)
    if needed > 0 or len(papers) < 4:
        openalex_papers = await search_openalex(query, max_results=max(needed, 4))
        existing_titles = {p["title"].lower().strip() for p in papers}
        for op in openalex_papers:
            if op["title"].lower().strip() not in existing_titles and len(papers) < max_results:
                papers.append(op)
                existing_titles.add(op["title"].lower().strip())
                
    # 3. Complement with Open Live Web Search (DuckDuckGo general internet scraping)
    if len(papers) < max_results:
        try:
            from app.utils.web_search import search_general_web
            web_papers = await search_general_web(query, max_results=max_results - len(papers))
            existing_titles = {p["title"].lower().strip() for p in papers}
            for wp in web_papers:
                if wp["title"].lower().strip() not in existing_titles and len(papers) < max_results:
                    papers.append(wp)
                    existing_titles.add(wp["title"].lower().strip())
        except Exception as e:
            print(f"Open web search complement error: {e}")

    return papers
