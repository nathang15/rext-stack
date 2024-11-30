from typing import List, Dict, Optional
from difflib import SequenceMatcher
import spacy
from ..retriever import Retriever
from ..graph import Graph
class Pipeline:
    def __init__(
        self, 
        documents: List[Dict], 
        triples: List[Dict], 
        excluded_tags: Optional[List[str]] = None,
        language_model: str = 'en_core_web_md'
    ):
        try:
            self.nlp = spacy.load(language_model)
        except OSError:
            print(f"Downloading language model {language_model}")
            spacy.cli.download(language_model)
            self.nlp = spacy.load(language_model)
        
        self.dictionary = {
            word.text.lower() for word in self.nlp.vocab 
            if word.is_alpha and len(word.text) > 1 and not word.is_stop
        }
        
        self.retriever = Retriever(documents=documents)
        self.graph = Graph(triples=triples)
        self.excluded_tags = set(excluded_tags) if excluded_tags else set()

    def spell_correction(self, query: str) -> str:
        def find_closest_word(word):
            if word.lower() in self.dictionary:
                return word
            
            try:
                closest = max(
                    self.dictionary, 
                    key=lambda x: SequenceMatcher(None, word.lower(), x).ratio()
                )
                return closest
            except ValueError:
                return word

        tokens = query.split()
        corrected_tokens = [find_closest_word(token) for token in tokens]
        
        return ' '.join(corrected_tokens)

    def search(
        self, 
        q: str, 
        tags: bool = False, 
        spell_correction: bool = True,
        k: int = 5
    ):
        if spell_correction:
            try:
                q = self.spell_correction(q)
            except Exception as e:
                print(f"Spell correction failed: {e}")
        
        if tags:
            return self.retriever.documents_tags(q)
        
        return self.retriever.documents(q)

    def __call__(
        self,
        q: str,
        k_tags: int = 20,
        k_yens: int = 3,
        k_walk: int = 3,
    ):
        documents = self.search(q)
        retrieved_tags = self.retriever.tags(q)

        tags = {}
        for document in documents:
            for tag in document.get('tags', []) + document.get('extra-tags', []):
                if tag not in self.excluded_tags:
                    tags[tag] = True

        nodes, links = self.graph(
            tags=list(tags)[:k_tags],
            retrieved_tags=retrieved_tags,
            k_yens=k_yens,
            k_walk=k_walk,
        )
        return documents, nodes, links

    def plot(
        self, 
        q: str, 
        k_tags: int = 20, 
        k_yens: int = 3, 
        k_walk: int = 3
    ):
        _, nodes, links = self(q=q, k_tags=k_tags, k_yens=k_yens, k_walk=k_walk)
        return nodes, links