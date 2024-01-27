from collections import Counter

import pandas as pd
from tqdm import tqdm

from .coauthors import CoAuthorshipGraph
from .utils import Neo4j
from .vis.fields_of_research import VisJS


class CitationFoRGraph(Neo4j, VisJS):
    """Field of Research interaction network from Wellcome Academic Graph citations.

    Attributes:
        node_source(str): Source node type for fields of research.
        edge_source(str): Source edge type to calculate field of research interactions.
        adjacency_matrices(dict): Adjacency matrix store for field of research networks.

    """

    def __init__(self, cypher_query=None, graph=True, s3_path=None):
        Neo4j.__init__(self, cypher_query, graph, s3_path)
        VisJS.__init__(self)

        self.node_source = "publications"
        self.edge_source = "citations"

        self.adjacency_matrices = {}

    @classmethod
    def from_publication_ids(cls, publication_ids, max_chunk_size=10000, s3_path=None):
        """Initialise Field of Research graph with publications
        from Dimensions IDs and their cited publications.

        Args:
            publication_ids(list): List of Dimensions IDs.
            max_chunk_size(int): Maximum number of IDs to query per chunk.
            s3_path(Optional[str]): Path to S3 bucket (including subdirectories) to back up query results to.

        """
        queries = []
        for i in range(0, len(publication_ids), max_chunk_size):
            query = f"""
            MATCH (f1:FieldOfResearch)<-[r1:RESEARCH_WITHIN]-(p1:Publication)-[:CITED_BY]->(p2:Publication)-[r2:RESEARCH_WITHIN]->(f2:FieldOfResearch)
            WHERE SIZE(f1.id)>2 AND SIZE(f2.id)>2 AND p2.dimensions_publication_id IN ['{"','".join(publication_ids[i:i+max_chunk_size])}']
            RETURN f2.name AS citing_for,f2.id AS citing_for_id,f1.name AS cited_for,f1.id AS cited_for_id, p2.year AS year, EXISTS {{
            MATCH (i)-[:FUNDED]->(p2)
            WHERE i.name='Wellcome Trust'
            }} AS Wellcome
            """
            queries.append(query)
        return cls(cypher_query=queries, graph=False, s3_path=s3_path)

    def adjacency_matrix_from_citations(self, year, funder=None):
        """Calculate adjacency matrix for a given year based on citations between fields.

        Args:
            year(int): Publication year of source publications.
            funder(Optional[str]): Name of funder to filter by.

        Returns:
            pd.DataFrame: Adjacency matrix of citations between fields.

        """
        df = self.data[self.data["year"] == year]
        if funder is not None:
            df = df[df[funder]]
        counts_df = pd.crosstab(df["citing_for"], df["cited_for"], margins=True)
        return counts_df

    def calculate_adjacency_matrices(self, funder=None):
        """Calculate yearly adjacency matrices for a given citations-based
        fields of research dataset. If a funder name is provided, also calculates
        adjacency matrices for that funder.

        Args:
            funder(optional[str]): Name of funder (optional).

        """
        self.data = pd.DataFrame(self.data)
        for year in self.data["year"].unique():
            print(year)
            self.adjacency_matrices[year] = {}
            adj_matrix = self.adjacency_matrix_from_citations(year=year)
            self.adjacency_matrices[year]["All"] = adj_matrix
            if funder is not None:
                adj_matrix = self.adjacency_matrix_from_citations(
                    year=year, funder=funder
                )
                self.adjacency_matrices[year][funder] = adj_matrix


class AuthorFoRGraph(CoAuthorshipGraph, VisJS):
    """Field of Research interaction network from Wellcome Academic Graph researchers.

    Attributes:
        node_source(str): Source node type for fields of research.
        edge_source(str): Source edge type to calculate field of research interactions.
        adjacency_matrices(dict): Adjacency matrix store for field of research networks.
        for_data(list): Data from Neo4j query returning fields of research per author.
        funder_data(list): Data from Neo4j query returning funding information per author.

    """

    def __init__(self):
        CoAuthorshipGraph.__init__(self)
        VisJS.__init__(self)

        self.node_source = "authors"
        self.edge_source = "coauthorships"

        self.adjacency_matrices = {}

        self.for_data = []
        self.funder_data = []

    def add_for_data_from_neo4j(self, chunk_size=500, s3_path=None):
        """Query Neo4j to return fields of research of each author's publications in the coauthorship graph.
        Data includes each author's Dimensions ID and the field of research name and publication year of the author's
        publication.

        Args:
            chunk_size(int): Maximum number of IDs to query per chunk.
            fname(Optional[str]): Filename to save back up of interim query results to.
            s3_path(Optional[str]): Path to S3 bucket (including subdirectories) to back up query results to.

        """
        self.for_data = []
        self.data = []
        queries = []
        researcher_ids = self.coauthorship_nodes["dimensions_researcher_id"].tolist()
        for i in range(0, len(researcher_ids), chunk_size):
            query = f"""
            MATCH (r:Researcher)-[:AUTHORED]-(p:Publication)-[:RESEARCH_WITHIN]-(f:FieldOfResearch)
            WHERE r.dimensions_researcher_id IN ['{"','".join(researcher_ids[i:i+chunk_size])}']
            AND SIZE(f.id)>2
            RETURN r.dimensions_researcher_id AS researcher, f.name AS for, p.year as year;
            """
            queries.append(query)
        self.query(query=queries, as_graph=False, s3_path=s3_path)
        self.for_data.extend(self.data)
        self.for_data = pd.DataFrame(self.for_data)

    def add_funder_data_from_neo4j(
        self, funder_name="Wellcome Trust", chunk_size=10000, s3_path=None
    ):
        """Query Neo4j to return funding information for each author. Data includes each funded author's
        Dimensions ID and the grant start and end dates.

        Args:
            funder_name(str): Name of funder.
            chunk_size(int): Maximum number of IDs to query per chunk.

        """
        self.data = []
        queries = []
        researcher_ids = self.coauthorship_nodes["dimensions_researcher_id"].tolist()
        for i in range(0, len(researcher_ids), chunk_size):
            query = f"""
            MATCH (f:Institution)-[:FUNDED]->(g:Grant)-[:AWARDED_TO]->(r:Researcher)
            WHERE r.dimensions_researcher_id IN ['{"','".join(researcher_ids[i:i+chunk_size])}']
                AND f.name ='{funder_name}'
            RETURN r.dimensions_researcher_id AS researcher, g.start_date AS start_date, g.end_date AS end_date
            """
            queries.append(query)
        self.query(query=queries, as_graph=False, s3_path=s3_path)
        df = pd.DataFrame(self.data)
        df["end_date"].fillna("2100", inplace=True)
        df["end_date"] = pd.to_datetime(df["end_date"])
        df["start_date"] = pd.to_datetime(df["start_date"])
        self.funder_data = df

    def add_for_data_from_file(self, bucket, prefix):
        """Load previously saved field of research data from Neo4j query.

        Args:
            bucket(str): Path to s3 bucket containing field of research data.
            prefix(Optional[str]): Path to subdirectory containing field of research data.

        """
        self.load_data_from_s3(bucket, prefix)
        self.for_data = pd.DataFrame(self.data)

    @staticmethod
    def _get_most_common(ls):
        """Extract most common item(s) from a list."""
        counter = Counter(ls)
        return [x for x, c in counter.most_common() if c == max(counter.values())]

    def get_coauthor_for_df(self, year, funder=False):
        """Filter fields of research data by year and funder such that it only contains data
        for researchers from their publications up to and including the specified year. If a funder
        is specified, only those researchers are returned which were funded by a grant starting before
        or up to the given year and ending during or after the given year.

        Args:
            year(int): Year of publication.
            funder(Optional[str]): Name of funder.

        Returns:
            pd.DataFrame: Most common field(s) of research for each author.

        """
        df = self.for_data.loc[self.for_data["year"] <= year, :]
        return df.groupby("researcher")["for"].apply(list).apply(self._get_most_common)

    @staticmethod
    def _extract_author_for_edges(edge):
        """Connect fields of research of author 1 to fields of research of author 2.

        Args:
            edge(triple):
                List of author 1 field(s) of research,
                list of author 2 field(s) of research,
                weight of coauthorship.

        Returns:
            list: New edges as dictionaries with author field tuples as keys and edge weights as values.

        """
        new_edges = Counter()
        for_a1, for_a2, w = edge
        for f in for_a1:
            for permutation in zip([f] * len(for_a2), for_a2):
                new_edges.update({tuple(sorted(permutation)): w})
                new_edges.update({tuple(sorted(permutation, reverse=True)): w})
        return new_edges

    def _convert_coauthor_edges(
        self, coauthor_edges, coauthor_for_df, funder=None, year=None
    ):
        """Convert coauthorship edges between researchers to coauthorship edges between
        the researchers' fields.

        Args:
            coauthor_edges(list): Edge triples containing author 1 Neo4j ID,
                author 2 Neo4j ID, coauthorship weight.
            coauthor_for_df(pd.DataFrame): Most common field(s) of research of each author.

        Returns:
            list: Edge triples containing author 1 fields of research list,
                author 2 fields of research list, and coauthorship weight.

        """
        for_edges = []
        missing = 0
        for e in coauthor_edges:
            a1, a2, w = e
            try:
                r1 = self._researcher_ids[a1]
                r2 = self._researcher_ids[a2]
                for_a1 = coauthor_for_df[r1]
                for_a2 = coauthor_for_df[r2]
                if funder is None:
                    for_edges.append((for_a1, for_a2, w))
                else:
                    funding = self.funder_data[
                        self.funder_data["researcher"].isin([r1, r2])
                    ]
                    if len(funding) > 0:
                        if any(
                            funding["start_date"] <= pd.to_datetime(str(year))
                        ) and any(funding["end_date"] >= pd.to_datetime(str(year))):
                            for_edges.append((for_a1, for_a2, w))
            except:
                missing += 1
        print(f"{len(for_edges)} author edges processed, {missing} missing.")
        return for_edges

    def get_author_for_edges(self, for_edges):
        """Convert coauthorship edges between authors to coauthorship edges between their
        most common fields of research.

        Args:
            for_edges(list): Edge triples containing author 1 fields of research list,
                author 2 fields of research list, and coauthorship weight.

        Returns:
            Counter: New edges as dictionaries with author field tuples as keys and edge weights as values.

        """
        edges = Counter()
        for edge in tqdm(for_edges):
            edge_counter = self._extract_author_for_edges(edge)
            if len(edge_counter) > 0:
                edges += edge_counter
        return edges

    def get_author_for_counts(self, year, funder=None):
        """Convert coauthorship edges from author IDs to fields of research and return
        new edges between fields.

        Args:
            year(int): Publication year of coauthorship edges to aggregate.
            funder(Optional[str]): Name of funder to filter by.

        Returns:
            Counter:  New edges as dictionaries with author field tuples as keys and edge weights as values.

        """
        coauthor_for_df = self.get_coauthor_for_df(year=int(year), funder=funder)
        for_edges = self._convert_coauthor_edges(
            self.coauthorship_edges[str(year)],
            coauthor_for_df,
            funder=funder,
            year=year,
        )
        return self.get_author_for_edges(for_edges)

    def adjacency_matrix_from_authors(self, year, funder=None):
        """Aggregate coauthorship edges by the authors' field(s) of research and return results in an
        adjacency matrix.

        Args:
            year(int): Publication year to consider for aggregation.
            funder(Optional[str]): Name of funder to coauthorships by.

        Returns:
            pd.DataFrame: Adjacency matrix between fields of research with
                weights representing the number of coauthorships.

        """
        new_edges = self.get_author_for_counts(year=year, funder=funder)
        df = pd.Series(new_edges).reset_index()
        df.columns = ["f1", "f2", "weight"]
        counts_df = pd.crosstab(
            df["f1"], df["f2"], values=df["weight"], aggfunc=sum, margins=True
        ).fillna(0)
        return counts_df

    def calculate_adjacency_matrices(self, funder=None):
        """Calculate yearly adjacency matrices for a given coauthorship-based
        fields of research dataset. If a funder name is provided, also calculates
        adjacency matrices for that funder.

        Args:
            funder(optional[str]): Name of funder (optional).

        """
        for year in [int(year) for year in self.coauthorship_edges.keys()]:
            print(year)
            self.adjacency_matrices[year] = {}
            adj_matrix = self.adjacency_matrix_from_authors(year=year)
            self.adjacency_matrices[year]["All"] = adj_matrix
            if funder is not None:
                adj_matrix = self.adjacency_matrix_from_authors(
                    year=year, funder=funder
                )
                self.adjacency_matrices[year][funder] = adj_matrix
