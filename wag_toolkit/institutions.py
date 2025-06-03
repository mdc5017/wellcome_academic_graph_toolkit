from collections import Counter
from itertools import combinations
import pandas as pd
from tqdm import tqdm

from .utils import Neo4j
from .vis.fields_of_research import VisJS


class Institutions(Neo4j, VisJS):
    """Institutions network from Wellcome Academic Graph.

    Attributes:
        coauthorship_nodes(list): Author nodes.
        coauthorship_edges(dict): Coauthorship edges for each publication year.

    """

    def __init__(self, cypher_query, graph=False):
        Neo4j.__init__(self, cypher_query, graph)
        VisJS.__init__(self)

        self.node_source = "authors"
        self.edge_source = "coauthorships"
        self.node_type = "institution"

        self.coauthorship_edges = {}
        self.institution_names = None
        self.publication_data = None
        self.adjacency_matrices = {}

    
    @classmethod
    def from_publication_ids(cls, publication_ids, max_chunk_size=10000):
        """Initialise coauthorship graph with publications
        from Dimensions IDs and their authors.

        Args:
            publication_ids(list): List of Dimensions IDs.
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """
        queries = []
        for i in range(0, len(publication_ids), max_chunk_size):
            query = f"""
            MATCH (r:Researcher)-[a:AUTHORED]->(p:Publication)
            WHERE p.dimensions_publication_id IN ['{"','".join(publication_ids[i:i+max_chunk_size])}']
            RETURN p.dimensions_publication_id AS dimensions_publication_id, p.year AS year,
                a.institutions AS grid_id
            """
            queries.append(query)
        return cls(queries)
    
    def institution_lookup(
        self,
        grid_ids,
        additional_columns=None,
        max_chunk_size=1000,
    ):
        self.data = []
        queries = []
        if additional_columns:
            query_add = "".join([f", c.{c} AS {c}" for c in additional_columns])
        else:
            query_add = ""
        for i in range(0, len(grid_ids), max_chunk_size):
            query = f"""
            MATCH (i:Institution)
            WHERE i.grid_id IN ['{"','".join(grid_ids[i:i+max_chunk_size])}']
            RETURN i.grid_id AS grid_id, i.name AS name {query_add}
            """
            queries.append(query)
        self.query(query=queries, as_graph=False)
        df = pd.DataFrame(self.data)
        return df