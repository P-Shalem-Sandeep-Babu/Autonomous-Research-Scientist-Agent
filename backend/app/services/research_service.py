import arxiv
from Bio import Entrez
from typing import List, Dict, Optional
import httpx
from app.core.config import settings
from app.core.cache import cache
import json

class ResearchService:
    """Service for fetching and processing research papers from arXiv and PubMed."""

    def __init__(self):
        self.arxiv_client = arxiv.Client()
        Entrez.email = settings.PUBMED_EMAIL  # Required for PubMed API

    async def fetch_arxiv_papers(self, query: str, max_results: int = 5) -> List[Dict]:
        """Fetch papers from arXiv based on a search query."""
        cache_key = f"arxiv_papers:{query}:{max_results}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return cached_result

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )

        papers = []
        for result in self.arxiv_client.results(search):
            papers.append({
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "summary": result.summary,
                "published": result.published.isoformat(),
                "url": result.entry_id,
                "pdf_url": result.pdf_url,
            })

        await cache.set(cache_key, papers, expire=3600)  # Cache for 1 hour
        return papers

    async def fetch_pubmed_papers(self, query: str, max_results: int = 5) -> List[Dict]:
        """Fetch papers from PubMed based on a search query."""
        cache_key = f"pubmed_papers:{query}:{max_results}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return cached_result

        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        handle.close()

        if not record["IdList"]:
            return []

        papers = []
        handle = Entrez.efetch(db="pubmed", id=record["IdList"], retmode="xml")
        records = Entrez.read(handle)
        handle.close()

        for article in records["PubmedArticle"]:
            paper = {
                "title": article["MedlineCitation"]["Article"]["ArticleTitle"],
                "authors": [
                    f"{author.get('ForeName', '')} {author.get('LastName', '')}"
                    for author in article["MedlineCitation"]["Article"].get("AuthorList", [])
                ],
                "abstract": article["MedlineCitation"]["Article"].get("Abstract", {}).get("AbstractText", ["No abstract available"])[0],
                "published": article["MedlineCitation"]["Article"]["Journal"]["JournalIssue"]["PubDate"].get("Year", "Unknown"),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{article['MedlineCitation']['PMID']}/",
            }
            papers.append(paper)

        await cache.set(cache_key, papers, expire=3600)  # Cache for 1 hour
        return papers

    async def summarize_text(self, text: str) -> str:
        """Summarize text using the Gemini API."""
        cache_key = f"summary:{text[:50]}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return cached_result

        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(f"Summarize this research text in 3-5 bullet points:\n\n{text}")
            summary = response.text
            await cache.set(cache_key, summary, expire=86400)  # Cache for 24 hours
            return summary
        except Exception as e:
            print(f"Error summarizing text: {e}")
            return "Summary unavailable."

    async def generate_citation(self, paper: Dict, style: str = "apa") -> str:
        """Generate a citation for a research paper in the specified style."""
        cache_key = f"citation:{style}:{paper.get('title', '')[:30]}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            return cached_result

        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"Generate a citation in {style} style for this paper:\n\n"
            if "title" in paper:
                prompt += f"Title: {paper['title']}\n"
            if "authors" in paper:
                prompt += f"Authors: {', '.join(paper['authors'])}\n"
            if "published" in paper:
                prompt += f"Year: {paper['published']}\n"
            if "url" in paper:
                prompt += f"URL: {paper['url']}\n"

            response = model.generate_content(prompt)
            citation = response.text
            await cache.set(cache_key, citation, expire=86400)  # Cache for 24 hours
            return citation
        except Exception as e:
            print(f"Error generating citation: {e}")
            return "Citation unavailable."

# Singleton instance
research_service = ResearchService()