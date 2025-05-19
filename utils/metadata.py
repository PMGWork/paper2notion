import requests
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

def is_similar(a, b, threshold=0.8):
    """2つの文字列の類似度がthreshold以上ならTrue"""
    return SequenceMatcher(None, a, b).ratio() >= threshold

def search_doi_by_title(title):
    """Crossrefでタイトル検索し、最も一致度の高いDOIを返す"""
    url = "https://api.crossref.org/works"
    params = {
        "query.title": title,
        "rows": 1,
        "sort": "relevance"
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return None
    items = resp.json().get("message", {}).get("items", [])
    if not items:
        return None
    return items[0].get("DOI")

def get_metadata_from_doi(doi):
    """DOIから論文のメタデータを取得する関数"""
    # arXiv IDの場合
    if doi.lower().startswith("arxiv:"):
        return _get_arxiv_metadata(doi)
    # 通常のDOI
    return _get_crossref_metadata(doi)

def _get_arxiv_metadata(arxiv_doi):
    """arXivからメタデータを取得"""
    arxiv_id = arxiv_doi.split(":")[1]
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None

    root = ET.fromstring(resp.text)
    entry = root.find("{http://www.w3.org/2005/Atom}entry")
    if entry is None:
        return None

    title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
    authors = [author.find("{http://www.w3.org/2005/Atom}name").text for author in entry.findall("{http://www.w3.org/2005/Atom}author")]
    summary = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip()
    published = entry.find("{http://www.w3.org/2005/Atom}published").text
    year = int(published[:4])
    arxiv_url = entry.find("{http://www.w3.org/2005/Atom}id").text

    return {
        "title": title,
        "authors": ", ".join(authors),
        "journals": "arXiv",
        "year": year,
        "doi": arxiv_url,
        "abstract": summary
    }

def _get_crossref_metadata(doi):
    """CrossRefからメタデータを取得"""
    url = f"https://api.crossref.org/works/{doi}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None

    data = resp.json()["message"]
    # "container-title"が空リストの場合に対応
    container_titles = data.get("container-title", [""])
    journals = container_titles[0] if container_titles else ""
    # "title"も同様にガード
    titles = data.get("title", [""])
    title = titles[0] if titles else ""
    return {
        "title": title,
        "authors": ", ".join([f'{a.get("given", "")} {a.get("family", "")}' for a in data.get("author", [])]),
        "journals": journals,
        "year": data.get("published-print", data.get("published-online", {})).get("date-parts", [[None]])[0][0],
        "doi": data.get("DOI", ""),
        "abstract": data.get("abstract", ""),
    }
