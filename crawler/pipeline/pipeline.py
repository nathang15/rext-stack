from ..retriever import Retriever
from ..graph import Graph
from typing import Tuple
import pkg_resources
from symspellpy import SymSpell

class Pipeline:
    def __init__(self, documents, triples, excluded_tags=None, max_edit_distance=2):
        self.retriever = Retriever(documents=documents)
        self.excluded_tags = {} if excluded_tags is None else excluded_tags
        self.graph = Graph(triples=triples)
        self.spell_checker = SymSpell(max_dictionary_edit_distance=max_edit_distance)
        dictionary_path = pkg_resources.resource_filename(
            "symspellpy", "frequency_dictionary_en_82_765.txt"
        )
        self.spell_checker.load_dictionary(dictionary_path, term_index=0, count_index=1)

    def correct_spelling(self, text: str) -> Tuple[str, bool]:
        suggestions = self.spell_checker.lookup_compound(
            text, max_edit_distance=2, transfer_casing=True
        )
        if suggestions:
            corrected = suggestions[0].term
            was_corrected = corrected != text
            return corrected, was_corrected
        return text, False

    def search(self, q: str, tags: bool = False, top_k: int = 100, apply_spelling: bool = True):
        if apply_spelling:
            corrected_q, was_corrected = self.correct_spelling(q)
            if was_corrected:
                print(f"Spell-corrected query: '{q}' -> '{corrected_q}'")
            q = corrected_q
            
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
        apply_spelling: bool = False
    ):
        if apply_spelling:
            corrected_q, was_corrected = self.correct_spelling(q)
            if was_corrected:
                print(f"Spell-corrected query: '{q}' -> '{corrected_q}'")
            q = corrected_q

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

    def plot(self, q: str, k_tags: int = 20, k_yens: int = 3, k_walk: int = 3, apply_spelling: bool = True):
        _, nodes, links = self(
            q=q, 
            k_tags=k_tags, 
            k_yens=k_yens, 
            k_walk=k_walk, 
            apply_spelling=apply_spelling
        )
        return nodes, links