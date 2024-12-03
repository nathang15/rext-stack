import copy
import typing
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from neural_search import retrieve
from lenlp import sparse

class Retriever:
    def __init__(self, documents: typing.Dict):
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        updated_documents = copy.deepcopy(documents)
        documents = [{"url": url, **document} for url, document in documents.items()]

        self.document_embeddings = {}
        for doc in documents:
            text = f"{doc['title']} {doc['summary']}"
            self.document_embeddings[doc['url']] = self.encoder.encode(text, convert_to_tensor=True)

        updated_documents = [
            {
                **{
                    "url": url,
                    "tags": " ".join(document.pop("tags", []) + document.pop("extra-tags", [])),
                },
                **document,
            }
            for url, document in updated_documents.items()
        ]

        self.retriever = (
            retrieve.TfIdf(
                key="url",
                attr=["title", "tags", "summary", "date"],
                k=50,
                tfidf=sparse.BM25Vectorizer(
                    normalize=True,
                    ngram_range=(4, 7),
                    analyzer="char_wb",
                    b=0.75,
                    k1=1.5,
                ),
                documents=updated_documents,
            )
            | retrieve.TfIdf(
                key="url",
                attr=["title", "tags", "summary", "date"],
                k=20,
                tfidf=sparse.BM25Vectorizer(
                    normalize=True,
                    ngram_range=(2, 5),
                    analyzer="char_wb",
                ),
                documents=updated_documents,
            )
        ) + documents

        self.retriever_documents_tags = (
            retrieve.TfIdf(
                key="url",
                attr=["title", "tags", "summary", "date"],
                k=60,
                tfidf=sparse.BM25Vectorizer(
                    normalize=True,
                    ngram_range=(4, 7),
                    analyzer="char_wb",
                ),
                documents=updated_documents,
            )
            & retrieve.TfIdf(
                key="url",
                attr=["tags"],
                k=60,
                tfidf=sparse.BM25Vectorizer(
                    normalize=True,
                    ngram_range=(4, 7),
                    analyzer="char_wb",
                ),
                documents=updated_documents,
            )
        ) + documents

        tags = {}
        for document in documents:
            for tag in document.get("tags", []) + document.get("extra-tags", []):
                tags[tag] = True
        self.tags_list = [{"tag": tag} for tag in tags]

        self.retriever_tags = (
            retrieve.TfIdf(
                key="tag",
                attr=["tag"],
                k=10,
                tfidf=sparse.BM25Vectorizer(
                    normalize=True,
                    ngram_range=(3, 7),
                    analyzer="char_wb",
                ),
                documents=self.tags_list,
            )
            + self.tags_list
        )

    def simple_rerank(self, query: str, documents: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        Rerank documents using a combination of bi-encoder and cross-encoder scores
        """
        if not documents:
            return []
            
        query_embedding = self.encoder.encode(query, convert_to_tensor=True)
        
        # Calculate bi-encoder similarities
        similarities = []
        for doc in documents:
            try:
                doc_embedding = self.document_embeddings[doc['url']]
                similarity = np.dot(query_embedding, doc_embedding)
                similarities.append(similarity)
            except KeyError:
                similarities.append(0.0)
                
        pairs = [[query, f"{doc['title']} {doc['summary']}" ] for doc in documents]
        
        # Only run cross-encoder if have pairs
        if pairs:
            cross_scores = self.cross_encoder.predict(pairs)
        else:
            cross_scores = []
            
        # Combine scores with weights
        combined_scores = [
            0.3 * sim + 0.7 * cross 
            for sim, cross in zip(similarities, cross_scores)
        ]
        
        # Sort documents by combined scores
        scored_docs = list(zip(documents, combined_scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return [doc for doc, _ in scored_docs[:top_k]]

    def documents(self, q: str, top_k: int = 10) -> List[Dict]:
        if not q.strip():
            return []
        initial_results = self.retriever(q)
        return self.simple_rerank(q, initial_results, top_k)

    def tags(self, q: str) -> List[str]:
        return [tag["tag"] for tag in self.retriever_tags(q)]

    def documents_tags(self, q: str, top_k: int = 10) -> List[Dict]:
        initial_results = self.retriever_documents_tags(q)
        return self.simple_rerank(q, initial_results, top_k)