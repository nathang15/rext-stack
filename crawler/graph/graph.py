import itertools
import typing
from typing import List, Dict, Any
import networkx as nx
import numpy as np

class Graph:
    def __init__(self, triples):
        self.graph = nx.Graph()

        nodes = {
            **{node["head"]: True for node in triples},
            **{node["tail"]: True for node in triples},
        }

        self.idx_to_node = {idx: node for idx, node in enumerate(nodes)}
        self.node_to_idx = {node: idx for idx, node in self.idx_to_node.items()}

        node_degrees = {}
        for triple in triples:
            head, tail = triple["head"], triple["tail"]
            node_degrees[head] = node_degrees.get(head, 0) + 1
            node_degrees[tail] = node_degrees.get(tail, 0) + 1
        
        for triple in triples:
            head = triple["head"]
            tail = triple["tail"]
            weight = (node_degrees.get(head, 1) + node_degrees.get(tail, 1)) / 2
            self.graph.add_edge(
                self.node_to_idx[head],
                self.node_to_idx[tail],
                weight=weight
            )
            self.graph.add_edge(
                self.node_to_idx[tail],
                self.node_to_idx[head],
                weight=weight
            )

    def __call__(
        self,
        tags: typing.List,
        retrieved_tags: typing.List,
        k_yens: int = 3,
        k_walk: int = 3,
    ):
        nodes, lonely = [], []
        output_nodes = {}

        colors = {
            'primary': "#86E5FF",
            'secondary': "#19bc8e",
            'neutral': "#FFFFFF",
            'highlight': "#FFB366"
        }

        for list_tag, color in [(tags, colors['primary']), (retrieved_tags, colors['secondary'])]:
            for tag in list_tag:
                idx = self.node_to_idx.get(tag, None)
                if idx is None:
                    lonely.append(tag)
                else:
                    nodes.append(idx)
                node_degree = len(list(self.graph.neighbors(self.node_to_idx.get(tag, -1)))) if idx is not None else 0
                size = 20 + min(node_degree * 5, 30)
                
                output_nodes[tag] = {
                    "id": tag,
                    "color": color,
                    "size": size
                }

        paths = []

        if len(nodes) >= 2:
            for start, end in itertools.combinations(nodes, 2):
                if start != end:
                    try:
                        new_paths = self.yens(start=start, end=end, k=k_yens)
                        paths.extend(new_paths)
                    except:
                        continue

        if len(nodes) == 1 or len(paths) == 0:
            for start in nodes:
                paths.append(self.walk(start=start, k=k_walk))

        for path in paths:
            for node in path:
                node_name = self.idx_to_node[node]
                if node_name not in output_nodes:
                    node_degree = len(list(self.graph.neighbors(node)))
                    size = 15 + min(node_degree * 3, 20)
                    
                    output_nodes[node_name] = {
                        "id": node_name,
                        "color": colors['neutral'],
                        "size": size
                    }

        return list(output_nodes.values()), self.format_triples(paths=paths)

    def yens(self, start: int, end: int, k: int):
        paths = []
        try:
            for idx, path in enumerate(nx.shortest_simple_paths(self.graph, start, end, weight="weight")):
                if len(path) <= 4:
                    paths.append(path)
                if idx >= k:
                    break
        except nx.NetworkXNoPath:
            pass
        return paths

    def walk(self, start: int, k: int):
        neighbours = [start]
        for n, node in enumerate(nx.all_neighbors(self.graph, start)):
            neighbours.append(node)
            if n > k:
                break
        return neighbours

    def format_triples(self, paths: typing.List[typing.List[str]]):
        triples = {}
        for path in paths:
            for start, end in zip(path[:-1], path[1:]):
                key = f"{min(start, end)}_{max(start, end)}"
                if key not in triples:
                    weight = self.graph[start][end].get("weight", 1.0)
                    triples[key] = {
                        "start": start,
                        "end": end,
                        "weight": weight
                    }

        links = []
        for triple in triples.values():
            head = self.idx_to_node[triple["start"]]
            tail = self.idx_to_node[triple["end"]]
            # Calculate edge opacity based on weight
            opacity = max(0.3, min(0.8, triple["weight"] / 3))
            links.append({
                "source": head,
                "target": tail,
                "relation": "link",
                "value": triple["weight"],
                "color": f"rgba(150,150,150,{opacity})"
            })

        return links