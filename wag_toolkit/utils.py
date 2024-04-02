import json
import os

import neo4j
import pandas as pd
import boto3
from tqdm import tqdm


class Neo4j:
    """Neo4j query helper to return data from the graph."""

    def __init__(self, cypher_query=None, lookup=None, graph=True, s3_path=None):
        """Initialise with Neo4j query results."""
        self._driver = neo4j.GraphDatabase.driver(
            os.environ["NEO4J_BOLT_URL"],
            auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
        )
        self.nodes = []
        self.edges = []
        self.data = []

        if lookup:
            self.lookup_query(query=cypher_query, lookup=lookup, as_graph=graph, s3_path=s3_path)
        else:
            self.query(query=cypher_query, as_graph=graph, s3_path=s3_path)

    def _transaction(self, tx, query, parameters, as_graph=True):
        """Run a query as Neo4j transaction."""
        result = tx.run(query, parameters)
        if as_graph:
            data = result.graph()
        else:
            data = result.data()
        result.consume()
        return data

    def query(self, query, parameters=None, db=None, as_graph=True, s3_path=None):
        """Run provided query and return results as nodes and edges.

        Args:
            query(str, list): Neo4j query string or list of query strings.
            parameters(list): Query parameters.
            db(str): Database name.
            as_graph(bool): Whether to return the results as graph or json format.
            s3_path(Optional[str]): Optional path to s3 bucket to save interim query results to.

        """
        if query is None:
            return None

        if not isinstance(query, list):
            query = [query]

        for i, q in enumerate(tqdm(query)):
            session = self._driver.session(database=db)
            try:
                if as_graph:
                    graph = session.read_transaction(self._transaction, q, parameters)
                    self.nodes.extend(list(graph._nodes.values()))
                    self.edges.extend(list(graph._relationships.values()))
                else:
                    data = session.read_transaction(
                        self._transaction, q, parameters, as_graph=False
                    )
                    if s3_path is not None:
                        self.save_data_to_s3(bucket=s3_path, fname=i, data=data)
                    self.data.extend(data)
            finally:
                session.close()
    
    def lookup_query(self, query, lookup, max_chunk_size=1000, as_graph=False, s3_path=None):
        """Run provided lookup query in batches.

        Args:
            query(str): Lookup query containing {} where the IDs will be inserted, e.g. 
                "MATCH (p:Publication) WHERE p.dimensions_publication_id IN {} RETURN *".
            lookup(list): List of IDs to look up.
            max_chunk_size(int): Maximum number of IDs to query per chunk.
            s3_path(Optional[str]): Optional path to s3 bucket to save interim query results to.

        """
        queries = []
        for i in range(0, len(lookup), max_chunk_size):
            lookup_string = "','".join(lookup[i: i + max_chunk_size])
            subquery = query.format(f"['{lookup_string}']")
            queries.append(subquery)
        self.query(queries, as_graph=as_graph, s3_path=s3_path)

    def to_df(self, node, dedupe=True):
        """Convert node properties to dataframe.

        Args:
            node(str): Node label, e.g. Publication

        Returns:
            pd.DataFrame: Properties of all nodes for a given label.
        """
        filtered = list(filter(lambda n: node in n._labels, self.nodes))
        df = pd.DataFrame([n._properties for n in filtered])
        df["id"] = [n.id for n in filtered]
        if dedupe:
            df.drop_duplicates(inplace=True, ignore_index=True)
        return df

    def save_data_to_s3(self, bucket, fname, data=None):
        """Utility function to save interim results from Neo4j query.

        Args:
            bucket(str): Destination bucket (full path including subdirectories) to save data to.
            fname(str): Name of file.
            data(Optional[dict]): Neo4j data in JSON format.

        """
        data = json.dumps(data)
        s3 = boto3.client("s3")

        s3.put_object(
            ACL="private",
            Body=data,
            Bucket=bucket,
            Key=f"{fname}.json",
        )

        s3.close()

    def load_data_from_s3(self, bucket, prefix):
        """Load previously saved data from Neo4j query.

        Args:
            bucket(str): Path to bucket containing data.
            prefix(Optional[str]): Path to subdirectory of interest.

        """
        s3 = boto3.client("s3")
        self.data = []
        fpaths = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        keys = [meta["Key"] for meta in fpaths["Contents"]]
        for key in keys:
            try:
                json_data = s3.get_object(Bucket=bucket, Key=key)
                data = json.loads(json_data["Body"].read())
                self.data.extend(data)
            except:
                print(f"Unable to load file: {key}.")

        s3.close()
