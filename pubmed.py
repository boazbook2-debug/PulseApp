import requests
import time
import streamlit as st

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

EVIDENCE_LABELS = {
    (0, 2): ("Meta-analyses & Systematic Reviews", "Strongest evidence"),
    (2, 4): ("Randomised Controlled Trials", "Strong evidence"),
    (4, 6): ("Observational Studies", "Moderate evidence"),
    (6, 8): ("Preliminary Research", "Early evidence"),
    (8, 11): ("Emerging & Exploratory Research", "Speculative"),
}

STUDY_FILTERS = {
    (0, 2): "systematic review[pt] OR meta-analysis[pt]",
    (2, 4): "randomized controlled trial[pt]",
    (4, 6): "observational study[pt] OR cohort study[pt]",
    (6, 8): "",
    (8, 11): "",
}

DEFAULT_QUERY = (
    '("sleep quality" OR "heart rate variability" OR "HRV" OR '
    '"wearable" OR "biometric" OR "circadian rhythm" OR "recovery" OR '
    '"physical activity" OR "resting heart rate" OR "sleep stages") '
    'AND ("health" OR "performance" OR "wellbeing")'
)


def get_evidence_label(slider_value):
    for (lo, hi), label in EVIDENCE_LABELS.items():
        if lo <= slider_value < hi:
            return label
    return ("Research", "")


def _get_study_filter(slider_value):
    for (lo, hi), f in STUDY_FILTERS.items():
        if lo <= slider_value < hi:
            return f
    return ""


@st.cache_data(ttl=3600)
def search_pubmed(query, slider_value, max_results=9):
    """Search PubMed and return list of article dicts. Cached for 1 hour."""
    study_filter = _get_study_filter(slider_value)
    full_query = f"({query}) AND ({study_filter})" if study_filter else query

    try:
        search_resp = requests.get(f"{PUBMED_BASE}/esearch.fcgi", params={
            "db": "pubmed",
            "term": full_query,
            "retmax": max_results,
            "sort": "relevance",
            "retmode": "json",
            "datetype": "pdat",
            "reldate": 1825,
        }, timeout=10)
        search_resp.raise_for_status()
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        time.sleep(0.35)

        summary_resp = requests.get(f"{PUBMED_BASE}/esummary.fcgi", params={
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json",
        }, timeout=10)
        summary_resp.raise_for_status()
        result = summary_resp.json().get("result", {})

        articles = []
        for pmid in ids:
            doc = result.get(pmid, {})
            if not doc or not doc.get("title"):
                continue
            authors = [a.get("name", "") for a in doc.get("authors", [])[:3]]
            articles.append({
                "pmid": pmid,
                "title": doc.get("title", "").rstrip("."),
                "authors": ", ".join(authors),
                "journal": doc.get("source", ""),
                "date": doc.get("pubdate", "")[:4],
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
        return articles

    except Exception:
        return []
