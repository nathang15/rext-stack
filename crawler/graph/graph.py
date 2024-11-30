import itertools
import typing
from typing import List, Dict, Any

import networkx as nx
import numpy as np

class Graph:

    def __init__(self, triples: List[Dict[str, str]]):
        """
        Init
        """
        nodes = set(triple['head'] for triple in triples) | \
                set(triple['tail'] for triple in triples)

        self.idx_to_node = np.array(list(nodes))
        self.node_to_idx = {node: idx for idx, node in enumerate(self.idx_to_node)}

        self.graph = nx.Graph()
        for triple in triples:
            head_idx = self.node_to_idx[triple['head']]
            tail_idx = self.node_to_idx[triple['tail']]
            self.graph.add_edge(head_idx, tail_idx)

    def __call__(
        self,
        tags: List[str],
        retrieved_tags: List[str],
        k_yens: int = 3,
        k_walk: int = 3
    ) -> tuple:
        """
        graph visualization
        """
        def generate_colors(tags, retrieved_tags):
            color_map = {}
            base_colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336']
            
            for idx, tag_list in enumerate([tags, retrieved_tags]):
                color = base_colors[idx % len(base_colors)]
                for tag in tag_list:
                    color_map[tag] = color
            
            return color_map

        color_map = generate_colors(tags, retrieved_tags)
        
        nodes, lonely = [], []
        output_nodes = {}

        for list_tag, is_primary in [(tags, True), (retrieved_tags, False)]:
            for tag in list_tag:
                idx = self.node_to_idx.get(tag)
                if idx is None:
                    lonely.append(tag)
                else:
                    output_nodes[tag] = {
                        "id": tag, 
                        "color": color_map.get(tag, "#A0A0A0")
                    }

        paths = self._find_paths(list(self.node_to_idx.get(tag) for tag in tags + retrieved_tags), 
                                 k_yens, k_walk)

        for path in paths:
            for node_idx in path:
                node = self.idx_to_node[node_idx]
                if node not in output_nodes:
                    output_nodes[node] = {
                        "id": node,
                        "color": "#E0E0E0"
                    }

        return list(output_nodes.values()), self.format_triples(paths)

    def _find_paths(self, nodes, k_yens, k_walk):
        """
        path finding
        """
        paths = []
        nodes = [n for n in nodes if n is not None]

        if len(nodes) >= 2:
            for start, end in itertools.combinations(nodes, 2):
                try:
                    paths.extend(
                        path for path in 
                        list(nx.shortest_simple_paths(self.graph, start, end))[:k_yens] 
                        if len(path) <= 5
                    )
                except nx.NetworkXNoPath:
                    continue

        if not paths and nodes:
            paths = [self.walk(start, k_walk) for start in nodes]

        return paths

    def walk(self, start: int, k: int) -> List[int]:
        """
        Perform a constrained random walk from a starting node
        """
        neighbours = [start]
        for node in nx.neighbors(self.graph, start):
            neighbours.append(node)
            if len(neighbours) >= k:
                break
        return neighbours

    def format_triples(self, paths: List[List[int]]) -> List[Dict[str, Any]]:
        """
        Convert node paths to link representations
        """
        unique_links = set()
        links = []

        for path in paths:
            for start, end in zip(path[:-1], path[1:]):
                if start != end:
                    link_key = tuple(sorted((start, end)))
                    if link_key not in unique_links:
                        unique_links.add(link_key)
                        links.append({
                            "source": self.idx_to_node[start],
                            "relation": "link",
                            "target": self.idx_to_node[end],
                            "value": 1
                        })

        return links