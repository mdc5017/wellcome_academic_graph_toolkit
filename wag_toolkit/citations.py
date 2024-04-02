from datetime import datetime

import networkx as nx
import pandas as pd
from dateutil import parser
from tqdm import tqdm

from .utils import Neo4j

# fast-cdindex is currently not available on PyPI. To optionally install it,
# follow the instructions on https://github.com/dspinellis/fast-cdindex
try:
    from fast_cdindex import cdindex
    from fast_cdindex.time_utilities import timestamp_from_datetime
except:
    import cdindex
    from cdindex import timestamp_from_datetime


class Citations(Neo4j):
    """Citations from Wellcome Academic Graph."""

    def __init__(self, cypher_query=None, lookup=None):
        super().__init__(cypher_query, lookup)
        self.filtered_ids = None

    @classmethod
    def from_publication_ids(cls, publication_ids, forward=True):
        """Initialise WAG with publications from
        Dimensions publication IDs and their citations or cited publications.

        Args:
            publication_ids(list): List of Dimensions IDs.
            forward(bool): Whether to load citing or cited publications.

        """
        if forward:
            direction = "-[r:CITED_BY]->"
        else:
            direction = "<-[r:CITED_BY]-"
        query = f"""
            MATCH (p:Publication){direction}(q)
            WHERE p.dimensions_publication_id IN {{}}
            RETURN *
            """
        return cls(query, lookup=publication_ids)

    def _add_cited(self, publication_ids, max_chunk_size=100):
        """Load publications cited by the publications provided in publication_ids.

        Args:
            publication_ids(list): List of Dimensions IDs.
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """
        query = """
            MATCH (c1:Publication)-[:CITED_BY]->(p:Publication)
            WHERE p.dimensions_publication_id IN {}
            RETURN p.dimensions_publication_id AS citing, p.date AS citing_pdate, p.year AS citing_pyear,
                c1.dimensions_publication_id AS cited, c1.date AS cited_pdate, c1.year AS cited_pyear
            """
        self.lookup_query(query, lookup=publication_ids, max_chunk_size=max_chunk_size, as_graph=False)

    def _add_citations(self, publication_ids, max_chunk_size=100):
        """Load publications citing the publications provided in publication_ids.

        Args:
            publication_ids(list): List of Dimensions IDs.
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """
        query = """
            MATCH (p:Publication)-[:CITED_BY]->(c2:Publication)
            WHERE p.dimensions_publication_id IN {}
            RETURN c2.dimensions_publication_id AS citing, c2.date AS citing_pdate, c2.year AS citing_pyear,
                p.dimensions_publication_id AS cited, p.date AS cited_pdate, p.year AS cited_pyear
            """
        self.lookup_query(query, lookup=publication_ids, max_chunk_size=max_chunk_size, as_graph=False)

    def add_cdindex_data(
        self, publication_ids, filter_by_year=True, max_chunk_size=100
    ):
        """Loads all data required to calculate the CD index for the publications provided in
        publication_ids.

        Args:
            publication_ids(list): List of Dimensions IDs.
            filter_by_year(bool): Filter out publications published before 2018 (where full set
                of citations has not been loaded to the graph) and after 2021 (to allow for a
                publication to accumulate a sufficient number of citations).
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """
        print("Adding cited publications")
        self._add_cited(publication_ids, max_chunk_size)
        df = pd.DataFrame(self.data)
        if filter_by_year:
            print("Filtering by year")
            df = df[(df["citing_pyear"] >= 2018) & (df["citing_pyear"] <= 2021)]
            self.filtered_ids = list(set(df["citing"].tolist()))
        else:
            self.filtered_ids = publication_ids
        cited_ids = list(set(df["cited"].tolist()))

        print("Adding citations")
        self._add_citations(self.filtered_ids, max_chunk_size)

        print("Adding cited publications' citations")
        self._add_citations(cited_ids, max_chunk_size)

    def to_networkx(self):
        """Convert nodes and edges to networkx DiGraph.

        Returns:
            nx.DiGraph: Networkx directed graph from neo4j nodes and edges.

        """
        nx_graph = nx.DiGraph()
        for node in self.nodes:
            nx_graph.add_node(
                node_for_adding=node.id,
                labels=list(node._labels),
                properties=node._properties,
            )
        for edge in self.edges:
            nx_graph.add_edge(
                edge.start_node.id,
                edge.end_node.id,
                key=edge.id,
                type=edge.type,
                properties=edge._properties,
            )
        return nx_graph

    def to_cdindex(self, chunksize=10000):
        """Convert nodes and edges to cdindex graph.

        Args:
            chunksize(int): Maximum size of chunks of data to load into CD index.

        Returns:
            cdindex.Graph: Graph format which enables calculating the CD index.

        """
        graph = cdindex.Graph()

        for i in tqdm(range(0, len(self.data), chunksize)):
            df = pd.DataFrame(self.data[i : i + chunksize])
            df.drop_duplicates(inplace=True)

            publication_dates = {}
            publication_dates.update(df.set_index("citing")["citing_pdate"].to_dict())
            publication_dates.update(df.set_index("cited")["cited_pdate"].to_dict())
            for publication_id, date in publication_dates.items():
                date = parser.parse(
                    date,
                    yearfirst=True,
                    default=datetime.strptime("2023-01-01", "%Y-%m-%d"),
                )
                try:
                    graph.add_vertex(publication_id, timestamp_from_datetime(date))
                except:
                    continue

            for start_node, end_node in zip(df["citing"], df["cited"]):
                try:
                    graph.add_edge(start_node, end_node)
                except:
                    continue

        return graph
