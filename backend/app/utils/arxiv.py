import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

async def search_arxiv(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search arXiv database for scientific papers.
    Query formatting: export.arxiv.org/api/query?search_query=all:{query}&max_results={max_results}
    """
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }
    
    headers = {
        "User-Agent": "AutonomousResearchScientistAgent/1.0"
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code != 200:
                print(f"arXiv API error: {response.status_code}")
                return []
                
            # Parse XML
            root = ET.fromstring(response.text)
            
            # XML Namespaces
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "opensearch": "http://a9.com/-/spec/opensearch/1.1/"
            }
            
            entries = root.findall("atom:entry", ns)
            papers = []
            
            for entry in entries:
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                published = entry.find("atom:published", ns)
                paper_id = entry.find("atom:id", ns)
                
                # Title clean up
                title_text = title.text.strip().replace("\n", " ") if title is not None else "Untitled"
                # Summary clean up
                summary_text = summary.text.strip().replace("\n", " ") if summary is not None else ""
                # Date clean up
                pub_date = published.text.strip() if published is not None else ""
                # ID extraction
                id_url = paper_id.text.strip() if paper_id is not None else ""
                pdf_url = id_url.replace("abs", "pdf") if "abs" in id_url else id_url
                
                # Authors
                authors = []
                for author in entry.findall("atom:author", ns):
                    name = author.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text.strip())
                authors_str = ", ".join(authors)
                
                papers.append({
                    "title": title_text,
                    "authors": authors_str,
                    "abstract": summary_text,
                    "url": id_url,
                    "pdf_url": pdf_url,
                    "source": "arXiv",
                    "pub_date": pub_date
                })
                
            return papers
            
    except Exception as e:
        print(f"Error querying arXiv: {e}")
        return []

# Quick test stub
if __name__ == "__main__":
    import asyncio
    async def main():
        res = await search_arxiv("brain tumor classification", max_results=2)
        for i, paper in enumerate(res):
            print(f"Paper {i+1}: {paper['title']}")
            print(f"Authors: {paper['authors']}")
            print(f"URL: {paper['url']}\n")
    asyncio.run(main())
