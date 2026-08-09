"""
Fixed: Issue 12 - NCBI key placeholder check
Fixed: Issue 19 - html entity unescaping
"""
import requests
import re
import html
from cache_manager import cache_get, cache_set
from utils import ncbi_limiter
from config import (
    PUBMED_SEARCH, PUBMED_FETCH,
    NCBI_API_KEY, _key_valid
)


def _unescape(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(
        r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text
    )
    return text.replace("\xa0", " ").strip()


def search_pubmed(
    query, max_papers=40, topic_type="nutrition"
):
    from config import normalise_condition
    query = normalise_condition(query) or query
    cache_key = f"pm_{query[:50]}_{max_papers}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    full_query = (
        f"({query})[Title/Abstract] AND "
        f"({topic_type} OR diet OR food OR "
        f"nutrition OR bioactive)[Title/Abstract]"
    )
    params = {
        "db": "pubmed",
        "term": full_query,
        "retmax": max_papers,
        "retmode": "json",
        "sort": "relevance"
    }
    # Fix 12: Only add key if it is a real key
    if _key_valid(NCBI_API_KEY):
        params["api_key"] = NCBI_API_KEY

    ncbi_limiter.wait()
    try:
        r = requests.get(
            PUBMED_SEARCH, params=params, timeout=30
        )
        r.raise_for_status()
        ids = (
            r.json()
            .get("esearchresult", {})
            .get("idlist", [])
        )
        if not ids:
            return []
    except Exception as e:
        print(f"[PubMed] Search error: {e}")
        return []

    ncbi_limiter.wait()
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "rettype": "xml",
        "retmode": "xml"
    }
    if _key_valid(NCBI_API_KEY):
        fetch_params["api_key"] = NCBI_API_KEY

    try:
        r2 = requests.get(
            PUBMED_FETCH,
            params=fetch_params,
            timeout=60
        )
        r2.raise_for_status()
        xml = r2.text
        articles = re.findall(
            r'<PubmedArticle>(.*?)</PubmedArticle>',
            xml, re.DOTALL
        )
        papers = []
        for i, art in enumerate(articles):
            try:
                pmid_m = re.search(
                    r'<PMID[^>]*>(\d+)</PMID>', art
                )
                pmid = (
                    pmid_m.group(1) if pmid_m
                    else (ids[i] if i < len(ids) else "")
                )
                title_m = re.search(
                    r'<ArticleTitle>(.*?)</ArticleTitle>',
                    art, re.DOTALL
                )
                title = _unescape(
                    re.sub(r'<[^>]+>', '',
                           title_m.group(1))
                ) if title_m else ""

                abs_parts = re.findall(
                    r'<AbstractText[^>]*>'
                    r'(.*?)</AbstractText>',
                    art, re.DOTALL
                )
                abstract = " ".join([
                    _unescape(
                        re.sub(r'<[^>]+>', '', p)
                    )
                    for p in abs_parts
                ])
                year_m = re.search(
                    r'<Year>(\d{4})</Year>', art
                )
                year = (
                    year_m.group(1) if year_m else ""
                )
                if abstract and len(abstract) > 50:
                    papers.append({
                        "pmid": pmid,
                        "title": title,
                        "abstract": abstract,
                        "year": year,
                        "url": (
                            f"https://pubmed.ncbi.nlm.nih.gov"
                            f"/{pmid}/"
                        )
                    })
            except Exception:
                continue
        cache_set(cache_key, papers)
        return papers
    except Exception as e:
        print(f"[PubMed] Fetch error: {e}")
        return []


def search_pubmed_microbiome(disease, max_papers=15):
    return search_pubmed(
        f"{disease} gut microbiome microbiota probiotics",
        max_papers, "microbiome"
    )