from collections import Counter
from itertools import combinations
import pandas as pd
from tqdm import tqdm

from .utils import Neo4j
from .vis.fields_of_research import VisJS


class Locations(Neo4j, VisJS):
    """Locations network from Wellcome Academic Graph.

    Attributes:
        coauthorship_nodes(list): Author nodes.
        coauthorship_edges(dict): Coauthorship edges for each publication year.

    """

    def __init__(self, cypher_query, graph=False):
        Neo4j.__init__(self, cypher_query, graph)
        VisJS.__init__(self)

        self.node_source = "authors"
        self.edge_source = "coauthorships"
        self.node_type = "country"

        self.coauthorship_edges = {}
        self.location_names = None
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

    def location_lookup(
        self,
        grid_ids,
        location_level="country",
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
            MATCH (i:Institution)-[:LOCATED_IN]->(c:{location_level.capitalize()})
            WHERE i.grid_id IN ['{"','".join(grid_ids[i:i+max_chunk_size])}']
            RETURN i.grid_id AS grid_id, c.{location_level} AS name {query_add}
            """
            queries.append(query)
        self.query(query=queries, as_graph=False)
        df = pd.DataFrame(self.data)
        return df

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

    @staticmethod
    def _extract_coauthorship_edges(author_info):
        edges = Counter()
        for c in combinations(author_info, 2):
            i1, i2 = c
            for i in i1:
                for permutation in zip([i] * len(i2), i2):
                    if isinstance(permutation[0], str) and isinstance(
                        permutation[1], str
                    ):
                        edges.update({tuple(sorted(permutation)): 1})
        return edges

    def _clean_grid_ids(self):
        self.data = pd.DataFrame(self.data)
        grid_ids = self.data["grid_id"].tolist()
        cleaned_grid_ids = []
        for g in grid_ids:
            if isinstance(g, str):
                if g == "[nan]":
                    cleaned_grid_ids.append([None])
                elif len(g.split(' '))>1:
                    cleaned = [
                        cg.strip().replace("'", "")
                        for cg in g.replace("['", "").replace("']", "").replace("\n", " ").split(" ")
                    ]
                    cleaned_grid_ids.append(cleaned)
                else:
                    cleaned = [
                        cg.strip()
                        for cg in g.replace("['", "").replace("']", "").split(",")
                    ]
                    cleaned_grid_ids.append(cleaned)
            else:
                cleaned_grid_ids.append(g)
        self.data["grid_id"] = cleaned_grid_ids

    def extract_edges(self, subset=None):
        data = self.data.dropna()
        if subset is not None:
            data = data[data["dimensions_publication_id"].isin(subset)]
        for year in tqdm(data["year"].unique()):
            df = data[data["year"] == year]
            edges = Counter()
            for g in df.groupby("dimensions_publication_id")["grid_id"].apply(list):
                edges.update(self._extract_coauthorship_edges(g))
            self.coauthorship_edges[year] = edges

    def extract_locations(self, location_level="country"):
        data = self.data.explode("grid_id").dropna()
        if location_level == "institution":
            location_info = self.institution_lookup(
                grid_ids=list(set(data["grid_id"].tolist()))
            )
        else:
            location_info = self.location_lookup(
                grid_ids=list(set(data["grid_id"].tolist())),
                location_level=location_level,
            )
        self.location_names = location_info.set_index("grid_id")["name"].to_dict()
        data["location"] = data["grid_id"].map(self.location_names)
        self.publication_data = data

    def convert_edges(self):
        converted_edges = {}
        for year, coauthorship_edges in self.coauthorship_edges.items():
            converted_edges[year] = Counter()
            for edge, weight in coauthorship_edges.items():
                grid_id_0, grid_id_1 = edge
                loc_0 = self.location_names.get(grid_id_0)
                loc_1 = self.location_names.get(grid_id_1)
                if isinstance(loc_0, str) and isinstance(loc_1, str):
                    converted_edges[year].update({(loc_0, loc_1): weight})
                    converted_edges[year].update({(loc_1, loc_0): weight})
        self.coauthorship_edges = converted_edges

    def calculate_adjacency_matrices(self):
        for year, edges in self.coauthorship_edges.items():
            if len(edges) > 0:
                print(year)
                self.adjacency_matrices[year] = {}
                df = pd.Series(edges).reset_index()
                df.columns = ["l1", "l2", "weight"]
                df = pd.crosstab(
                    df["l1"], df["l2"], values=df["weight"], aggfunc=sum, margins=True
                ).fillna(0)
                df.loc["total", :] = df.columns.map(
                    self.publication_data[self.publication_data["year"] == year][
                        "location"
                    ]
                    .value_counts()
                    .to_dict()
                )
                self.adjacency_matrices[year]["All"] = df

    def extract(self, subset=None, location_level="country"):
        self._clean_grid_ids()
        self.extract_edges(subset=subset)
        self.extract_locations(location_level=location_level)
        self.convert_edges()
        self.calculate_adjacency_matrices()
