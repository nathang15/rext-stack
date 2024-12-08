import codecs
from ..retriever import Retriever
from ..graph import Graph
from typing import Dict, Tuple
import pkg_resources
from symspellpy import SymSpell, Verbosity

class Pipeline:
    def __init__(self, documents, triples, excluded_tags=None, max_edit_distance=2):
        self.retriever = Retriever(documents=documents)
        self.excluded_tags = {} if excluded_tags is None else excluded_tags
        self.graph = Graph(triples=triples)
        self.spell_checker = SymSpell(max_dictionary_edit_distance=max_edit_distance)
        dictionary_path = pkg_resources.resource_filename(
            "symspellpy", "frequency_dictionary_en_500_000.txt"
        )
        with codecs.open(dictionary_path, 'r', encoding='cp437') as dictionary_file:
            self.spell_checker._load_dictionary_stream(
                dictionary_file,
                term_index=0,
                count_index=1
            )

    def get_spelling_suggestion(self, text: str) -> Dict[str, str]:
        """Returns spelling suggestion and its confidence"""
        suggestions = self.spell_checker.lookup_compound(
            text, 
            max_edit_distance=2,
            transfer_casing=True,
            ignore_non_words=True
        )
        
        if not suggestions:
            words = text.split()
            corrected_words = []
            
            for word in words:
                word_suggestions = self.spell_checker.lookup(
                    word,
                    Verbosity.ALL,
                    max_edit_distance=2,
                    transfer_casing=True,
                    include_unknown=True
                )
                
                if word_suggestions:
                    best_suggestion = word_suggestions[0]
                    if best_suggestion.distance <= 1:
                        corrected_words.append(best_suggestion.term)
                    else:
                        corrected_words.append(word)
                else:
                    corrected_words.append(word)
            
            corrected_text = " ".join(corrected_words)
            
            if corrected_text != text:
                return {
                    "suggestion": corrected_text,
                    "confidence": "high" if all(w in word_suggestions and w.distance <= 1 for w in words) else "medium"
                }
            
        elif suggestions[0].term != text:
            return {
                "suggestion": suggestions[0].term,
                "confidence": "high" if suggestions[0].distance <= 1 else "medium"
            }
            
        return {"suggestion": None, "confidence": None}

    def search(self, q: str, tags: bool = False, top_k: int = 100):
        if tags:
            return self.retriever.documents_tags(q, top_k)
        return self.retriever.documents(q, top_k)

    def __call__(
        self,
        q: str,
        k_tags: int = 20,
        k_yens: int = 3,
        k_walk: int = 3,
        top_k: int = 10,
    ):
        documents = self.retriever.documents(q, top_k)
        retrieved_tags = [tag for tag in self.retriever.tags(q) if tag not in self.excluded_tags]

        tags = {}
        for document in documents:
            doc_tags = [tag for tag in (document.get("tags", []) + document.get("extra-tags", [])) 
                    if tag not in self.excluded_tags]
            for tag in doc_tags:
                tags[tag] = tags.get(tag, 0) + 1

        sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
        top_tags = [tag for tag, _ in sorted_tags[:k_tags]]

        triples = []
        for doc in documents:
            doc_tags = [tag for tag in (doc.get("tags", []) + doc.get("extra-tags", []))
                    if tag not in self.excluded_tags]
            for i, tag1 in enumerate(doc_tags):
                for tag2 in doc_tags[i+1:]:
                    if tag1 != tag2:
                        triples.append({
                            "head": tag1,
                            "tail": tag2
                        })

        nodes, links = self.graph(
            tags=top_tags,
            retrieved_tags=retrieved_tags,
            k_yens=k_yens,
            k_walk=k_walk,
        )
        return documents, nodes, links

    def plot(self, q: str, k_tags: int = 20, k_yens: int = 3, k_walk: int = 3):
        _, nodes, links = self(
            q=q, 
            k_tags=k_tags, 
            k_yens=k_yens, 
            k_walk=k_walk
        )
        return nodes, links