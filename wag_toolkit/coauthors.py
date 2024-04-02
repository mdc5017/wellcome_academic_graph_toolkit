import json
import os
from collections import Counter
from functools import partial
from itertools import combinations
from multiprocessing import Pool

import boto3
import awswrangler as wr
import networkx as nx
import pandas as pd
from tqdm import tqdm

from .utils import Neo4j


class CoAuthorshipGraph(Neo4j):
    """Co-authorship network from Wellcome Academic Graph.

    Attributes:
        coauthorship_nodes(list): Author nodes.
        coauthorship_edges(dict): Coauthorship edges for each publication year.

    """

    def __init__(self, cypher_query=None, lookup=None):
        super().__init__(cypher_query, lookup)

        self.coauthorship_nodes = []
        self.coauthorship_edges = {}
        self._researcher_ids = {}

    @classmethod
    def from_publication_ids(cls, publication_ids):
        """Initialise coauthorship graph with publications
        from Dimensions IDs and their authors.

        Args:
            publication_ids(list): List of Dimensions IDs.

        """
        query = """
            MATCH (r:Researcher)-[a:AUTHORED]->(p:Publication)
            WHERE p.dimensions_publication_id IN {} RETURN *
            """
        return cls(query, lookup=publication_ids)

    @classmethod
    def from_researcher_ids(cls, researcher_ids):
        """Initialise coauthorship graph with publications from Dimensions IDs and their authors.

        Args:
            publication_ids(list): List of Dimensions IDs.

        """
        query = """
            MATCH (r1:Researcher)-[a1:AUTHORED]->(p:Publication)<-[a2:AUTHORED]-(r2)
            WHERE r1.dimensions_researcher_id IN {} RETURN *
            """
        return cls(query, lookup=researcher_ids)

    def from_file(self, bucket, directory):
        """Load coauthor nodes and edges from files.

        Args:
            bucket(str): S3 bucket containing nodes and edges data.
            directory(str): Directory containing nodes and edges data.

        """
        self.coauthorship_nodes = wr.s3.read_csv(
            f"s3://{bucket}/{directory}/coauthor_nodes.csv"
        )
        self.coauthorship_nodes.drop_duplicates(inplace=True, ignore_index=True)
        self._researcher_ids = self.coauthorship_nodes.set_index("id")[
            "dimensions_researcher_id"
        ].to_dict()

        s3 = boto3.client("s3")

        json_data = s3.get_object(Bucket=bucket, Key=f"{directory}/coauthor_edges.json")
        data = json.loads(json_data["Body"].read())
        self.coauthorship_edges = data

        s3.close()

    @staticmethod
    def _extract_author_edges(publication_node, edges):
        """Extract all coauthor edges for a given publication node.

        Args:
            publication_node(int): Publication node id.

        Returns:
            list: Edges between two coauthors as frozensets.

        """
        pa_edges = list(filter(lambda edge: edge[1] == publication_node, edges))
        aa_edges = [frozenset(c) for c in combinations([e[0] for e in pa_edges], 2)]
        return aa_edges

    def collate_edge_lists(self, nodes, edges):
        """Extract all coauthor edges via publications using multiprocessing.

        Args:
            nodes(iterable): Publication nodes.
            edges(list): All edges returned from Neo4j.

        Returns:
            list: Edges between coauthors as frozensets.

        """
        with Pool(os.cpu_count()) as pool:
            edge_list = list(
                tqdm(
                    pool.map(partial(self._extract_author_edges, edges=edges), nodes),
                    total=len(nodes),
                )
            )
        return edge_list

    @staticmethod
    def _calculate_edge_weights(edge_lists):
        """Calculate edge weights.

        Args:
            edge_lists(list): List of coauthorship edge lists.

        Returns:
            list: Triples consisting of author 1, author 2, and weight representing
                the number of coauthored publications.

        """
        edge_list = []
        edgecount = Counter([e for el in edge_lists for e in el])
        for edgeset, weight in edgecount.items():
            e1, e2 = list(edgeset)
            edge_list.append((e1, e2, weight))
        return edge_list

    def extract_coauthorship_edges(self):
        """Extract coauthorship edges from Neo4j graph data.
        Edges are extracted and weights calculated for each publication year.

        """
        publication_nodes = list(
            filter(lambda node: "Publication" in node._labels, self.nodes)
        )
        for year in {p._properties["year"] for p in publication_nodes}:
            print(year)
            publication_nodes_filtered = [
                p.id
                for p in filter(
                    lambda node: node._properties["year"] == year, publication_nodes
                )
            ]
            edges_all = [(e.start_node.id, e.end_node.id) for e in self.edges]

            edge_lists = self.collate_edge_lists(
                nodes=publication_nodes_filtered, edges=edges_all
            )
            self.coauthorship_edges[year] = self._calculate_edge_weights(
                edge_lists=edge_lists
            )

    def extract_coauthorship_nodes(self):
        """Convert Researcher node properties to dataframe."""
        self.coauthorship_nodes = self.to_df("Researcher")
        self._researcher_ids = self.coauthorship_nodes.set_index("id")[
            "dimensions_researcher_id"
        ].to_dict()

    def extract_coauthorship_nodes_and_edges(self):
        """Extract author node metadata and coauthorship edges from Neo4j graph data."""
        self.extract_coauthorship_nodes()
        self.extract_coauthorship_edges()

    def to_networkx(self):
        """Convert nodes and edges to NetworkX co-authorship graph,
        where edges are weighted by publication year.

        Returns:
            nx.MultiGraph: Undirected, weighted co-authorship graph from Neo4j nodes and edges.

        """
        G = nx.MultiGraph()
        for year in self.coauthorship_edges.keys():
            G.add_weighted_edges_from(self.coauthorship_edges, year=year)
        nx.set_node_attributes(
            G,
            self.coauthorship_nodes.drop_duplicates().set_index("id").to_dict("index"),
        )
        return G

    def to_file(self, bucket, directory):
        """Save coauthorship nodes and edges to files.
        Dataframe containing node IDs and properties will be saved as csv, edges will be saved as JSON.

        Args:
            bucket(str): Destination S3 bucket.
            directory(str): Destination directory to save data to.

        """
        wr.s3.to_csv(
            df=self.coauthorship_nodes,
            path=f"s3://{bucket}/{directory}/coauthor_nodes.csv",
        )

        self.save_data_to_s3(
            bucket=bucket,
            fname=f"{directory}/coauthor_edges",
            data=self.coauthorship_edges,
        )
