import collections
import itertools
import typing
from functools import lru_cache

from neural_search import retrieve
from sklearn.feature_extraction.text import TfidfVectorizer

__all__ = ["get_extra_tags", "get_tags_triples"]


def get_tags_triples(data: typing.Dict, excluded_tags=None):
    excluded_tags = set(excluded_tags or [])
    
    seen_pairs = set()
    triples = []

    for document in data.values():
        tags = set(document["tags"] + document.get("extra-tags", []))
        
        for head, tail in itertools.combinations(tags, 2):
            if head in excluded_tags or tail in excluded_tags:
                continue

            pair = frozenset((head, tail))
            if pair not in seen_pairs:
                triples.append({"head": head, "tail": tail})
                seen_pairs.add(pair)

    return triples

def get_extra_tags(data: typing.Dict) -> typing.Dict:
    documents = {}
    tagged = {}

    for url, document in data.items():
        doc_tags = set(document["tags"])
        documents.update((tag, True) for tag in doc_tags)
        tagged[url] = doc_tags

    documents_list = [{"tag": tag} for tag in documents]

    retriever = (
        retrieve.Flash(
            key="tag",
            attr="tag",
            k=10,
        )
        | retrieve.TfIdf(
            key="tag",
            attr="tag",
            documents=documents_list,
            k=3,
            tfidf=TfidfVectorizer(
                lowercase=True, 
                ngram_range=(4, 7), 
                analyzer="char_wb"
            ),
        )
    ).add(documents_list)

    extra_tags = {}
    for url, document in data.items():
        query_text = f"{document.get('title', '')} {document.get('summary', '')}"
        
        extra_tags[url] = [
            tag["tag"]
            for tag in retriever(query_text)
            if (tag["Similarity"] > 0.2 and 
                tag["tag"] not in tagged[url])
        ]

    return {
        url: {**document, "extra-tags": extra_tags[url]} 
        for url, document in data.items()
    }