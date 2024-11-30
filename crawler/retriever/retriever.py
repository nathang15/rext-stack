import copy
import typing

from neural_search import retrieve, rerank
from lenlp import sparse
from sentence_transformers import SentenceTransformer
__all__ = ["Retriever"]


class Retriever:
    def __init__(
        self, 
        documents: typing.Dict, 
        embedding_model=SentenceTransformer(f"sentence-transformers/all-mpnet-base-v2").encode,
        query_encoder=SentenceTransformer('facebook-dpr-question_encoder-single-nq-base').encode,
        dpr_encoder=SentenceTransformer('facebook-dpr-ctx_encoder-single-nq-base').encode,
    ):
        updated_documents = copy.deepcopy(documents)
        documents = [{"url": url, **document} for url, document in documents.items()]

        updated_documents = [
            {
                **{
                    "url": url,
                    "tags": " ".join(document.pop("tags") + document.pop("extra-tags")),
                },
                **document,
            }
            for url, document in updated_documents.items()
        ]

        # Base TF-IDF retriever
        base_retriever = (
            retrieve.TfIdf(
                key="url",
                attr=["title", "tags", "summary", "date"],
                k=30,
                tfidf=sparse.BM25Vectorizer(    
                    normalize=True,
                    ngram_range=(4, 7),
                    analyzer="char_wb",
                    b=0,
                ),
                documents=updated_documents,
            )
            | retrieve.TfIdf(
                key="url",
                attr=["title", "tags", "summary", "date"],
                k=10,
                tfidf=sparse.BM25Vectorizer(
                    normalize=True,
                    ngram_range=(2, 5),
                    analyzer="char_wb",
                ),
                documents=updated_documents,
            )
        )

        # Tag-specific retriever
        tag_retriever = (
            retrieve.TfIdf(
                key="url",
                attr=["title", "tags", "summary", "date"],
                k=40,
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
                k=40,
                tfidf=sparse.BM25Vectorizer(
                    normalize=True,
                    ngram_range=(4, 7),
                    analyzer="char_wb",
                ),
                documents=updated_documents,
            )
        )

        # Prepare tags
        tags = {}
        for document in documents:
            for tag in document["tags"] + document["extra-tags"]:
                tags[tag] = True
        tags = [{"tag": tag} for tag in tags]

        # Tag retriever
        tag_search = (
            retrieve.TfIdf(
                key="tag",
                attr=["tag"],
                k=5,
                tfidf=sparse.BM25Vectorizer(
                    normalize=True,
                    ngram_range=(3, 7),
                    analyzer="char_wb",
                ),
                documents=tags,
            )
            + tags
        )

        if embedding_model:
            base_retriever += rerank.Encoder(
                key="url", 
                attr=["title", "tags", "summary", "date"],
                encoder=embedding_model
            )

        if query_encoder and dpr_encoder:
            base_retriever += rerank.DPR(
                key="url",
                attr=["title", "tags", "summary", "date"],
                encoder=dpr_encoder,
                query_encoder=query_encoder
            )

        self.retriever = base_retriever + documents
        self.retriever_documents_tags = tag_retriever + documents
        self.retriever_tags = tag_search

    def documents(self, q: str):
        return self.retriever(q)

    def tags(self, q: str):
        return [tag["tag"] for tag in self.retriever_tags(q)]

    def documents_tags(self, q: str):
        return self.retriever_documents_tags(q)