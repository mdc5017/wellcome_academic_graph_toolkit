import numpy as np
import pandas as pd
from collections import Counter
from .utils import read_from_s3

from .utils import Neo4j

class IDR(Neo4j):
    """Metrics for Interdisciplinarity Research"""

    def __init__(self, cypher_query=None, s3_path=None, weighted=None):
        Neo4j.__init__(self, cypher_query, graph=False)
        self.fields = pd.read_csv("scripts/input/anzsrc2020.csv")
        self.fields["sub_group"] = self.fields["sub_group"].apply(lambda x: x.title())
        self.super_groups = list(
            self.fields["super_group"].apply(lambda x: x.title()).unique()
        )

        if weighted:
            self.cosine_similarity = read_from_s3(
                s3_path + "/cosine_similarity.csv"
            ).drop(["Unnamed: 0"], axis=1)
            self.citation_similarity = read_from_s3(
                s3_path + "/citation_similarity.csv"
            ).drop(["Unnamed: 0"], axis=1)
            self.cosine_similarity.index = self.super_groups
            self.citation_similarity.index = self.super_groups
        else:
            self.cosine_similarity = None
            self.citation_similarity = None

    def format_fields(self, fields):
        """Format Neo4J string Fields of Research (FoR) to match ANZSRC.

        Args:
            fields(list): List of lists for each grant/publication and its unformatted fields.

        """

        unique_fields = [x.strip("'").split(" ") for x in fields]
        formatted_list = [
            [item.replace("_", " ").title() for item in sublist]
            for sublist in unique_fields
        ]
        return formatted_list

    def convert_to_supergroup(self, fields):
        """Look-up super groups for each subfield.

        Args:
            fields(list): List of lists for each grant/publication and its formatted fields.

        Returns:
            super_groups(list): List of unique super group fields

        """

        super_group_fields = []
        for item in fields:
            super_group = []
            for f in item:
                try:
                    super_group.append(
                        self.fields[self.fields["sub_group"] == f]["super_group"]
                        .values[0]
                        .title()
                    )
                except:
                    pass
                if f in self.super_groups:
                    super_group.append(f)
            super_group_fields.append(list(set(super_group)))
        return super_group_fields
    
    def researcher_fields(self, researcher_fields):
        try:
            formatted_fields = self.format_fields(researcher_fields)
            super_groups = self.convert_to_supergroup(formatted_fields)
            flattened_list = [item for sublist in super_groups for item in sublist]
            counts = Counter(flattened_list)
            return counts.most_common()
        except:
            return np.nan

    def top_fields(self, tally):
        if len(tally) >= 2:
            top1 = tally[0][0]
            top2 = tally[1][0]
        elif len(tally) == 1:
            top1 = tally[0][0]
            top2 = None
        else:
            top1 = None
            top2 = None
        return (top1, top2)

    @classmethod
    def get_grant_field(cls, grant_ids, max_chunk_size=10000):
        """Query FoR linked to grant IDs

        Args:
            grant_ids(list): List of grant IDs
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """

        queries = []
        for i in range(0, len(grant_ids), max_chunk_size):
            query = f"""
                    MATCH (g:Grant)
                    WHERE g.dimensions_grant_id IN {grant_ids[i: i + max_chunk_size]}
                    RETURN id(g), g.original_source_id, g.dimensions_grant_id, g.for, g.start_date
                    """
            queries.append(query)
        return cls(queries, graph=False)

    @classmethod
    def get_grantees(cls, grant_ids, max_chunk_size=10000):
        """Query PI's linked to grant IDs

        Args:
            grant_ids(list): List of grant IDs
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """

        queries = []
        for i in range(0, len(grant_ids), max_chunk_size):
            query = f"""
                    MATCH (g:Grant)-[a:AWARDED_TO]->(r:Researcher)
                    WHERE g.dimensions_grant_id IN {grant_ids[i: i + max_chunk_size]}
                    RETURN id(g), g.dimensions_grant_id, g.original_source_id, g.start_date, id(r), r.first_name, r.last_name
                    """
            queries.append(query)
        return cls(queries, graph=False)

    @classmethod
    def get_researcher_publications(cls, researchers, max_chunk_size=10000):
        """Query PI's publications linked to researcher IDs

        Args:
            researchers(list): List of researcher IDs
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """

        queries = []
        for i in range(0, len(researchers), max_chunk_size):
            query = f"""
                    MATCH (r:Researcher)-[a:AUTHORED]->(p:Publication)
                    WHERE id(r) IN {researchers[i: i + max_chunk_size]}
                    RETURN id(r), COLLECT(p.for)
                    """
            queries.append(query)
        return cls(queries, graph=False)
    
    @classmethod
    def get_grantee_publications(cls, researchers, max_chunk_size=10000):
        """Query PI's publications linked to grant IDs

        Args:
            grant_ids(list): List of grant IDs
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """

        queries = []
        for researcher, year, grant in researchers:
            for i in range(0, len(researcher), max_chunk_size):
                query = f"""
                        MATCH (g:Grant)-[l:AWARDED_TO]-(r:Researcher)-[a:AUTHORED]->(p:Publication)
                        WHERE id(r) = {researcher[i: i + max_chunk_size]} AND p.year <= {year[i: i + max_chunk_size]} AND id(g) = {grant[i: i + max_chunk_size]}
                        RETURN id(r), id(g), COLLECT(p.for)
                        """
                queries.append(query)
        return cls(queries, graph=False)

    @classmethod
    def get_grant_publications(cls, grants, max_chunk_size=10000):
        """Query publications linked to grant IDs

        Args:
            grant_ids(list): List of grant IDs
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """

        queries = []
        for i in range(0, len(grants), max_chunk_size):
            query = f"""
                    MATCH (g:Grant)-[l:LINKED_TO]-(p:Publication)
                    WHERE g.dimensions_grant_id IN {grants[i: i + max_chunk_size]}
                    RETURN id(g), COLLECT(p.for)
                    """
            queries.append(query)
        return cls(queries, graph=False)

    @classmethod
    def get_publication_fors(cls, pub_ids, max_chunk_size=10000):
        """Query publication FoRs

        Args:
            pub_ids(list): List of pub IDs
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """

        queries = []
        for i in range(0, len(pub_ids), max_chunk_size):
            query = f"""
                    MATCH (p:Publication)
                    WHERE p.dimensions_publication_id IN {pub_ids[i: i + max_chunk_size]}
                    RETURN id(p), p.dimensions_publication_id, p.date, COLLECT(p.for)
                    """
            queries.append(query)
        return cls(queries, graph=False)

    @classmethod
    def reference_list(cls, pub_ids, max_chunk_size=10000):
        """Query FoRs to references from publication.

        Args:
            pub_ids(list): List of publication IDs.
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """

        queries = []
        for i in range(0, len(pub_ids), max_chunk_size):
            query = f"""
                MATCH (c:Publication)-[r:CITED_BY]->(p:Publication)
                WHERE p.dimensions_publication_id IN {pub_ids[i: i + max_chunk_size]}
                RETURN id(p), p.dimensions_publication_id, p.date, p.for, COLLECT(id(c)), COLLECT(c.for)
                """
            queries.append(query)
        return cls(queries, graph=False)

    @classmethod
    def citation_list(cls, pub_ids, delay, max_chunk_size=10000):
        """Query FoRs from citations to publication.

        Args:
            pub_ids(list): List of publication IDs.
            max_chunk_size(int): Maximum number of IDs to query per chunk.

        """

        queries = []
        for i in range(0, len(pub_ids), max_chunk_size):
            query = f"""
                MATCH (p:Publication)-[r:CITED_BY]->(c:Publication)
                WHERE p.dimensions_publication_id IN {pub_ids[i: i + max_chunk_size]} AND c.year - p.year <= {delay}
                RETURN id(p), p.date, p.dimensions_publication_id, p.for, COLLECT(c.date), COLLECT(id(c)), COLLECT(c.for)
                """
            queries.append(query)
        return cls(queries, graph=False)

    def simpson(self, counts):
        """Calculate Simpsons Diversity without replacement.
        
        Args:
            count(Counter): Super group counts.

        """

        values_fors = list(reversed([i[1] for i in counts]))
        d = 0
        V = sum(values_fors)
        if V > 1:
            for i, v in enumerate(values_fors):
                d += v * (v - 1) / (V * (V - 1))
            return 1 - d
        else:
            return np.nan

    def unweighted_rs(self, counts):
        """Calculate probability that any samples are not the same without replacement.
        
        Args:
            count(Counter): Super group counts.
            
        """

        values_fors = list(reversed([i[1] for i in counts]))
        V = sum(values_fors)
        d = 0
        if V > 1:
            for i, x in enumerate(values_fors):
                for j, y in enumerate(values_fors):
                    if i != j:
                        d += (x / V) * ((y - 1) / (V - 1))
            return d
        else:
            return np.nan

    def rao_stirling(self, counts, w):
        """Calculate Rao-Stirling Diversity.
        
        Args:
            count(Counter): Super group counts.
            w(pd.DataFrame): Similarity matrix.
        """

        values_fors = list(reversed([i[1] for i in counts]))
        field_fors = list(reversed([i[0] for i in counts]))
        V = sum(values_fors)
        d = 0
        if V > 1:
            for i, x in enumerate(values_fors):
                for j, y in enumerate(values_fors):
                    if i != j:
                        field1 = field_fors[i]
                        field2 = field_fors[j]
                        d += (x / V) * ((y - 1) / (V - 1)) * (1 - w[field1][field2])
            return d
        else:
            return np.nan
        
    def grant_fields(self, grant_ids):
        """Retrieve fields associated to each grant and unique super-groups.

        Args:
            grant_ids(list): List of grant IDs

        """
        grant_fors = self.get_grant_field(grant_ids).data
        grant_fields = pd.DataFrame(grant_fors)
        grant_fields["all_fields"] = self.format_fields(grant_fields["g.for"])
        grant_fields["super_groups"] = self.convert_to_supergroup(
            grant_fields["all_fields"]
        )
        return grant_fields
    
    def query_to_diversity(self, df, for_col = "COLLECT(p.for)"):
        """Process and format query data and calculate diversity.
        
        Args:
            df(pd.DataFrame): queried data as dataframe.
            for_cols(str): string to index FoR column.
        """
        
        df["no_pubs"] = df[for_col].apply(lambda x: len(x))
        df["super_group_counts"] = df[for_col].apply(
            lambda x: self.researcher_fields(x)
        )
        df["top_supergroups"] = df["super_group_counts"].apply(
            lambda x: self.top_fields(x)
        )
        df["simpson_diversity"] = df[
            "super_group_counts"
        ].apply(lambda x: self.simpson(x))

        if self.cosine_similarity is not None:
            df["rs_cosine"] = df["super_group_counts"].apply(
                lambda x: self.rao_stirling(x, self.cosine_similarity)
            )

        if self.citation_similarity is not None:
            df["rs_citation"] = df["super_group_counts"].apply(
                lambda x: self.rao_stirling(x, self.citation_similarity)
            )

        if for_col == "COLLECT(c.for)":
            df["pub_fields"] = df["p.for"].apply(
                lambda x: self.researcher_fields([x])
            )
        return df

    def grantees_fields(self, grant_ids, max_chunk_size=10000):
        """Retrieve researchers linked to to each grant and calculate 
        diversity of their publication history.

        Args:
            grant_ids(list): List of grant IDs

        """

        grantees = self.get_grantees(grant_ids, max_chunk_size=10000).data
        researchers = [[i["id(r)"], int(i["g.start_date"][:4]), i["id(g)"]] for i in grantees]
        publications = self.get_grantee_publications(
            researchers, max_chunk_size=max_chunk_size
        ).data
        researchers_df = pd.DataFrame(publications)

        if len(researchers_df) != 0:
            researchers_df = self.query_to_diversity(researchers_df)
            merged = researchers_df.merge(pd.DataFrame(grantees))
            return merged
        else:
            return None

    def grant_publication_fields(self, grant_ids):
        """Retrieve fields associated to each grant and calculate
        diversity of grant publication outputs.

        Args:
            grant_ids(list): List of grant IDs

        """
        grant_pub_fors = self.get_grant_publications(grant_ids).data
        grant_pub_fields = pd.DataFrame(grant_pub_fors)
        if len(grant_pub_fields) != 0:
            grant_pub_fields = self.query_to_diversity(grant_pub_fields)
            return grant_pub_fields    
        else:
            return None        

    def publication_fields(self, pub_ids):
        """Retrieve fields associated to publicand unique super-groups.

        Args:
            grant_ids(list): List of grant IDs

        """
        pub_fors = self.get_publication_fors(pub_ids).data
        pub_fields = pd.DataFrame(pub_fors)
        if len(pub_fields) != 0:
            pub_fields = self.query_to_diversity(pub_fields)
            return pub_fields
        else:
            return None

    def knowledge_integration(self, pub_ids, max_chunk_size=10000):
        """Retrieve fields associated to each grant and unique super-groups.

        Args:
            grant_ids(list): List of grant IDs

        """
        ref_fors = self.reference_list(pub_ids, max_chunk_size).data
        ref_fields = pd.DataFrame(ref_fors)
        if len(ref_fields) != 0:
            ref_fields = self.query_to_diversity(ref_fields, for_col = "COLLECT(c.for)")
            ref_fields["no_refs"] = ref_fields["no_pubs"]
            return ref_fields
        else:
            return None

    def knowledge_diffusion(self, pub_ids, delay=25, max_chunk_size=10000):
        """Retrieve fields associated to each grant and unique super-groups.

        Args:
            grant_ids(list): List of grant IDs

        """
        cite_fors = self.citation_list(pub_ids, delay, max_chunk_size).data
        cite_fields = pd.DataFrame(cite_fors)
        if len(cite_fields) != 0:
            cite_fields = self.query_to_diversity(cite_fields, for_col = "COLLECT(c.for)")
            cite_fields["no_cite"] = cite_fields["no_pubs"]
            return cite_fields
        else:
            return None
