import boto3
import pandas as pd
import sys
from datetime import datetime
from dateutil import parser

from tqdm import tqdm
import multiprocessing
from io import StringIO
import numpy as np

sys.path.append("../../toolkit")
from wag_toolkit.utils import Neo4j
from currency_converter import CurrencyConverter


class CareerStage(Neo4j):
    """Class for career stage analysis for Wellcome Academic Graph"""

    def __init__(self):
        """
        Initialise the class to deal with the Career / Researcher analysis for DR
        """
        super().__init__()
        self.bucket = "datalabs-data"

        # paths to existing data sources
        self.DR_pub_grant_links_path = (
            "funding_impact_measures/dr_grants/dr_pub_grant_links.xlsx"
        )
        self.FOR_hierarchy_directory_path = "dimensions/careers/anzsrc2020.csv"
        self.DR_schemes_mapping_path = "dimensions/careers/DRscheme_mapping.xlsx"

        # paths to directories to save query ouputs
        self.pub_ids_path = "dimensions/careers/pub_ids"
        self.batches_researchers_path = "dimensions/careers/pub_ids_batches/researchers"
        self.researchers_adam_path = "dimensions/careers/grant_info_adam.csv"
        self.researchers_collated_path = "dimensions/careers/researchers_collated.csv"
        self.researchers_processed_path = "dimensions/careers/researchers_processed.csv"
        self.researchers_exploded_path = "dimensions/careers/exploded_career_data/researchers_exploded"
        
        # variables
        
        self.RCR_log_threshold = 2.1


    def load_DR_pub_grant_links(self):
        """
        Loads the mapping from DR grants to publications that Adam queried via the Dimensions API
        """
        print("loading DR grant to pub mappings from s3", end="")
        s3 = boto3.client("s3")
        excel_file = s3.get_object(Bucket=self.bucket, Key=self.DR_pub_grant_links_path)
        self.DR_pub_grant_links = pd.read_excel(excel_file["Body"].read())
        self.DR_pub_ids = set(self.DR_pub_grant_links["id"])
        print("... finished")

    def load_pub_ids(self):
        """
        Loads all publications related to DR from saved csv file
        """
        tqdm.pandas()
        self.load_FOR_hierarchy()

        print("loading DR pub ids from s3", end="")
        s3 = boto3.client("s3")
        csv_file = s3.get_object(Bucket=self.bucket, Key=self.pub_ids_path)
        content = csv_file["Body"].read().decode("utf-8")
        lines = content.strip().split("\n")[1:]
        self.pubs_id = {line.split(",")[1] for line in lines}
        self.pubs_info = pd.read_csv(StringIO(content))

    def load_DR_scheme_mapping(self):
        """
        Load the DR scheme mapping
        """
        print("loading DR schema mappings from s3", end="")
        s3 = boto3.client("s3")
        excel_file = s3.get_object(Bucket=self.bucket, Key=self.DR_schemes_mapping_path)
        self.DR_scheme_mapping = pd.read_excel(
            excel_file["Body"].read(), sheet_name="by_ref"
        )
        self.DR_scheme_mapping.rename(
            columns={
                "Master Grant Type Name": "Master_Grant_Type_Name",
                "Open mode / Directed": "Open_mode_directed",
            },
            inplace=True,
        )
        print("... finished")

    def load_career_info_adam(self):
        """
        Loads all publications related to DR from saved csv file
        """
        print("loading grant_info from s3", end="")
        s3 = boto3.client("s3")
        csv_file = s3.get_object(Bucket=self.bucket, Key=self.researchers_adam_path)
        content = csv_file["Body"].read().decode("utf-8")
        self.career_info_adam = pd.read_csv(StringIO(content))

        print("... finished")

    def load_FOR_hierarchy(self):
        """
        Loads all publications related to DR from saved csv file
        """
        print("loading FOR hierarchy from s3", end="")
        s3 = boto3.client("s3")
        csv_file = s3.get_object(
            Bucket=self.bucket, Key=self.FOR_hierarchy_directory_path
        )
        content = csv_file["Body"].read().decode("utf-8")
        self.FOR_hierarchy = pd.read_csv(StringIO(content))

        # make a dictionary from FOR to one of the 23 FOR super groups
        self.FOR_hierarchy = pd.Series(
            [
                item.lower().replace(" ", "_")
                for item in self.FOR_hierarchy.super_group.values
            ],
            index=[
                item.lower().replace(" ", "_") for item in self.FOR_hierarchy.sub_group
            ],
        ).to_dict()
        print("... finished")

    def load_career_collated_data(self):
        """
        Loads the career data (one line per publication)
        """
        print("loading career data from s3", end=" ")
        s3 = boto3.client("s3")
        combined_df = []
        s3_objects = s3.list_objects(
            Bucket=self.bucket, Prefix=self.researchers_collated_path
        )
        for s3_object in s3_objects.get("Contents", []):
            file_key = s3_object["Key"]
            if file_key.endswith(".csv"):
                response = s3.get_object(Bucket=self.bucket, Key=file_key)
                content = response["Body"].read().decode("utf-8")
                df = pd.read_csv(StringIO(content))
                combined_df.append(df)
                print(".", end="")

        self.career_data_collated = pd.concat(combined_df, ignore_index=True)
        print(" finished")

    def load_career_processed_data(self):
        """
        Loads the career data (one line per publication)
        """
        print("loading career data from s3", end=" ")
        s3 = boto3.client("s3")
        combined_df = []
        s3_objects = s3.list_objects(
            Bucket=self.bucket, Prefix=self.researchers_processed_path
        )
        for s3_object in s3_objects.get("Contents", []):
            file_key = s3_object["Key"]
            if file_key.endswith(".csv"):
                response = s3.get_object(Bucket=self.bucket, Key=file_key)
                content = response["Body"].read().decode("utf-8")
                df = pd.read_csv(StringIO(content))
                combined_df.append(df)
                print(".", end="")

        self.career_data_processed = pd.concat(combined_df, ignore_index=True)
        self.career_data_processed["date"] = pd.to_datetime(
            self.career_data_processed["date"], format="%Y-%m-%d"
        )
        print(" finished")

    def load_career_data_exploded(self):
        """
        Loads the exploded career data (grouped by researcher)
        """
        print("loading career info (exploded) from s3", end=" ")
        s3 = boto3.client("s3")
        combined_df = []
        s3_objects = s3.list_objects(
            Bucket=self.bucket, Prefix=self.researchers_exploded_path
        )
        for s3_object in s3_objects.get("Contents", []):
            file_key = s3_object["Key"]
            if file_key.endswith(".csv"):
                response = s3.get_object(Bucket=self.bucket, Key=file_key)
                content = response["Body"].read().decode("utf-8")
                df = pd.read_csv(StringIO(content))
                combined_df.append(df)
                print(".", end="")
            if file_key.endswith(".json"):
                self.load_data_from_s3(self.bucket, self.researchers_exploded_path)
                self.career_data_exploded = self.data
                return
        self.career_data_exploded = pd.concat(combined_df, ignore_index=True)

    @staticmethod
    def parse_date(date_string):
        """
        Utility function to parse the various date formats into one datetime format
        """
        date_datetime = parser.parse(
            date_string,
            yearfirst=True,
            default=datetime.strptime("2023-01-01", "%Y-%m-%d"),
        )
        return date_datetime

    def extract_pubs_ids(self):
        """
        Extracts pub ids for pubs of the last 20 years
        """
        # find publication years:
        years = list(range(2002, 2024))
        queries = []
        for year in years:
            query = f"""MATCH (p:Publication)
                    WHERE p.year = {year}
                    RETURN
                    p.dimensions_publication_id as dimensions_publication_id,
                    p.for as pub_FOR,
                    p.relative_citation_ratio as RCR;
                    """
            queries.append(query)

        self.query(query=queries, as_graph=False)

        # save to s3
        s3 = boto3.client("s3")

        self.pubs_info = pd.DataFrame(self.data)

        # resolve FOR to their super group
        self.pubs_info["pub_FOR"] = self.pubs_info["pub_FOR"].apply(
            lambda x: eval(x).split(" ") if isinstance(x, str) else []
        )

        print("resolve FOR to super group")
        self.pubs_info["pub_FOR_super"] = self.pubs_info["pub_FOR"].progress_apply(
            lambda x: set([self.FOR_hierarchy[y] for y in x if y in self.FOR_hierarchy])
        )

        print("... finished")

        pd.DataFrame(self.pubs_info).to_csv("pubs_ids.csv", index=False)
        s3.upload_file("pubs_ids.csv", self.bucket, self.pub_ids_path)

    def career_info_adam(self):
        """
        retrieve career info for researchers working on publications
        from Adam's DR grants-publication mapping
        """
        self.load_DR_pub_grant_links()
        DR_pub_grant_links = self.DR_pub_grant_links

        grant_ids = list(DR_pub_grant_links["grant_id"].unique())
        pub_ids = list(DR_pub_grant_links["id"].unique())

        # do a query to get all the information related to grants
        print(f"finding career info related to grants from Adam's links")

        grant_query = f"""
            OPTIONAL MATCH (i:Institution)-[:FUNDED]->(g:Grant)-[:AWARDED_TO]->(r:Researcher)-[rel:AUTHORED]->(p:Publication)
            WHERE g.dimensions_grant_id IN ['{"','".join([str(grant_id) for grant_id in grant_ids])}']
            RETURN
            p.dimensions_publication_id as dimensions_publication_id,
            p.relative_citation_ratio as RCR,
            p.for as pub_FOR,
            p.date as date,
            p.year as year,
            r.dimensions_researcher_id AS dimensions_researcher_id,
            r.first_name AS first_name,
            r.last_name AS last_name,
            rel.position AS author_position,
            g.dimensions_grant_id as dimensions_grant_id,
            g.funding_amount AS funding_amount,
            g.funding_currency AS funding_currency,
            g.title AS grant_title,
            g.for AS grant_FOR,
            g.start_date AS grant_start_date,
            i.name AS funder;
            """

        self.query(query=grant_query, as_graph=False)
        grant_df = pd.DataFrame(self.data)

        self.data = []

        # do a query to get all information related to publications
        print(f"finding career info related to publications from Adam's links")

        pub_query = f"""
            OPTIONAL MATCH (i:Institution)-[:FUNDED]->(g:Grant)-[:AWARDED_TO]->(r:Researcher)-[rel:AUTHORED]->(p:Publication)
            WHERE p.dimensions_publication_id IN ['{"','".join(pub_ids)}']
            RETURN
            p.dimensions_publication_id as dimensions_publication_id,
            p.relative_citation_ratio as RCR,
            p.for as pub_FOR,
            p.date as date,
            p.year as year,
            r.dimensions_researcher_id AS dimensions_researcher_id,
            r.first_name AS first_name,
            r.last_name AS last_name,
            rel.position AS author_position,
            g.dimensions_grant_id as dimensions_grant_id,
            g.funding_amount AS funding_amount,
            g.funding_currency AS funding_currency,
            g.title AS grant_title,
            g.for AS grant_FOR,
            g.start_date AS grant_start_date,
            i.name AS funder;
            """

        self.query(query=pub_query, as_graph=False)
        pub_df = pd.DataFrame(self.data)

        career_info_adam = pd.concat([grant_df, pub_df], ignore_index=True)
        career_info_adam = career_info_adam.drop_duplicates()

        # save to s3
        s3 = boto3.client("s3")
        pd.DataFrame(career_info_adam).to_csv("grant_info_adam.csv")
        s3.upload_file("grant_info_adam.csv", self.bucket, self.researchers_adam_path)

    def career_info_wac(self, chunk_size=10000):
        """
        retrieve career info for researchers working in FOR of interest
        """
        self.data = []

        # load pub ids
        self.load_pub_ids()
        pub_ids = list(self.pubs_id)

        chunks = [
            pub_ids[i : i + chunk_size] for i in range(0, len(pub_ids), chunk_size)
        ]
        pool_chunks = [(chunks[i], i) for i in range(0, len(chunks))]

        global researchers_from_pub_ids

        def researchers_from_pub_ids(pub_ids, idx):
            neo = Neo4j()
            neo.query(
                f"""
                OPTIONAL MATCH (i:Institution)-[:FUNDED]->(g:Grant)-[:AWARDED_TO]->(r:Researcher)-[rel:AUTHORED]->(p:Publication)
                WHERE p.dimensions_publication_id IN ['{"','".join(pub_ids)}']
                AND i.name IN ['Wellcome Trust', 'The Francis Crick Institute', 'Medical Research Council', 'National Institute for Health Research']
                RETURN
                p.dimensions_publication_id as dimensions_publication_id,
                p.relative_citation_ratio as RCR,
                p.for as pub_FOR,
                p.date as date,
                p.year as year,
                r.dimensions_researcher_id AS dimensions_researcher_id,
                r.first_name AS first_name,
                r.last_name AS last_name,
                rel.position AS author_position,
                g.dimensions_grant_id as dimensions_grant_id,
                g.funding_amount AS funding_amount,
                g.funding_currency AS funding_currency,
                g.title AS grant_title,
                g.for AS grant_FOR,
                g.start_date AS grant_start_date,
                i.name AS funder;
                """,
                as_graph=False,
                s3_path="datalabs-data",
                fpath=f"{self.batches_researchers_path}_{idx}",
            )
            print(f"finished batch {idx}")

        pool = multiprocessing.Pool(processes=10)
        pool.starmap(researchers_from_pub_ids, pool_chunks)
        # Close the Pool to release resources
        pool.close()
        pool.join()

    def collate_career_info(self):
        """
        merge all researcher .json outputs from extracted from the graph and adams grant-publication map
        """
        tqdm.pandas()

        self.data = []
        self.load_career_info_adam()
        self.load_data_from_s3(self.bucket, self.batches_researchers_path)

        career_data = pd.DataFrame(self.data)
        print(f"found {len(career_data)} matches in the graph")
        print(f"found {len(self.career_info_adam)} matches in Adam's sheet")
        career_data = pd.concat([career_data, self.career_info_adam], ignore_index=True)
        print(f"found {len(career_data)} matches after joining")
        career_data = career_data.dropna(subset=["dimensions_researcher_id"])
        print(f"found {len(career_data)} matches that have a researcher linked to it")

        # convert amounts to USD
        c2c = CurrencyConverter()

        def convert_item_to_usd(amount, currency):
            try:
                return c2c.convert(amount, currency, "USD")
            except ValueError:
                return None

        # some pubs are duplicated because more than one grant, so add all funding amount and deduplicate
        career_data["funding_amount_usd"] = career_data.progress_apply(
            lambda x: convert_item_to_usd(x.funding_amount, x.funding_currency), axis=1
        )

        pub_funding = (
            career_data[["dimensions_publication_id", "funding_amount_usd"]]
            .groupby(by="dimensions_publication_id")
            .agg(sum)
        )
        pub_id2pub_funding = pd.Series(
            pub_funding.funding_amount_usd.values, index=pub_funding.index
        ).to_dict()
        career_data["funding_amount_usd"] = career_data[
            "dimensions_publication_id"
        ].map(pub_id2pub_funding)

        career_data = career_data.drop_duplicates(
            subset=["dimensions_publication_id", "dimensions_grant_id", "dimensions_researcher_id"],
            ignore_index=True,
        )
        print(f"found {len(career_data)} matches after aggregating grants")
        self.data = []

        # save data to s3
        csv_buffer = StringIO()
        career_data.to_csv(csv_buffer, index=False)
        s3_resource = boto3.resource("s3")
        s3_resource.Object(self.bucket, self.researchers_collated_path).put(
            Body=csv_buffer.getvalue()
        )

    def process_career_info(self):
        """
        Take the collated research outputs from collate_career_info, process and save to s3
        """
        tqdm.pandas()
        self.load_DR_scheme_mapping()
        self.load_DR_pub_grant_links()
        self.load_career_collated_data()
        self.load_FOR_hierarchy()
        career_data = self.career_data_collated

        # load in Adam's pub - grants links so we can add in ref numbers
        DR_pub_grant_links = self.DR_pub_grant_links
        grant_id2ref = pd.Series(
            DR_pub_grant_links.Reference.values, index=DR_pub_grant_links.grant_id
        ).to_dict()

        # add in reference
        print(f"add in references where a grant_id matches DR grant_id")
        grant_id2ref[np.nan] = np.nan
        career_data["reference"] = career_data["dimensions_grant_id"].map(grant_id2ref)

        # add in DR scheme
        print(f"add in DR scheme where a matching grant reference is found")
        grant_id2ref = pd.Series(
            self.DR_scheme_mapping.Open_mode_directed.values,
            index=self.DR_scheme_mapping.Reference.values,
        ).to_dict()
        career_data["DR_scheme"] = career_data["reference"].map(grant_id2ref)

        # parse dates
        if career_data["date"].dtype != "<M8[ns]":
            print("parsing dates")
            career_data["date"] = career_data["date"].progress_apply(self.parse_date)

        # add in column to check if "Wellcome" is in the funder name
        if "funder_wellcome" not in career_data.keys():
            print("determining if Wellcome is the funder")
            career_data["funder_wellcome"] = career_data["funder"].progress_apply(
                lambda x: "wellcome" in x.lower()
            )

        # add in column to check if "Sanger" is in the funder name
        if "funder_MRC" not in career_data.keys():
            print("determining if MRC is the funder")
            career_data["funder_MRC"] = career_data["funder"].progress_apply(
                lambda x: "medical research council" in x.lower()
            )

        # add in column to check if "Crick" is in the funder name
        if "funder_crick" not in career_data.keys():
            print("determining if Crick is the funder")
            career_data["funder_crick"] = career_data["funder"].progress_apply(
                lambda x: "crick" in x.lower()
            )

        # add in column to check if "Crick" is in the funder name
        if "funder_NIHR" not in career_data.keys():
            print("determining if NIHR is the funder")
            career_data["funder_NIHR"] = career_data["funder"].progress_apply(
                lambda x: "national institute for health research" in x.lower()
            )

        # add in a column to check if a pub_id is related to DR
        if "funder_DR" not in career_data.keys():
            print("determining if a publication is related to DR")
            career_data["funder_DR"] = career_data[
                "dimensions_publication_id"
            ].progress_apply(lambda x: x in self.DR_pub_ids)

        # resolve FOR to their super group
        career_data["pub_FOR"] = career_data["pub_FOR"].apply(
            lambda x: eval(x).split(" ") if isinstance(x, str) else []
        )
        career_data["grant_FOR"] = career_data["grant_FOR"].apply(
            lambda x: eval(x).split(" ") if isinstance(x, str) else []
        )

        print("resolve FOR to super group")
        career_data["pub_FOR_super"] = career_data["pub_FOR"].progress_apply(
            lambda x: set([self.FOR_hierarchy[y] for y in x if y in self.FOR_hierarchy])
        )
        career_data["grant_FOR_super"] = career_data["grant_FOR"].progress_apply(
            lambda x: set([self.FOR_hierarchy[y] for y in x if y in self.FOR_hierarchy])
        )

        career_data["RCR_log"] = career_data["RCR"].progress_apply(lambda x: np.log(x))

        print(f"RCR log threshold for 95 percentile is {self.RCR_log_threshold}")
        career_data["RCR_log_above_threshold"] = career_data[
            "RCR_log"
        ].progress_apply(lambda x: x >= self.RCR_log_threshold)


        # save data to s3
        print("saving to s3")
        csv_buffer = StringIO()
        career_data.to_csv(csv_buffer, index=False)
        s3_resource = boto3.resource("s3")
        s3_resource.Object(self.bucket, self.researchers_processed_path).put(
            Body=csv_buffer.getvalue()
        )

    def process_career_info_exploded(self):
        """
        process the career information and metadata so we can make some visualisations
        """
        tqdm.pandas()

        # load dataframes for joining
        self.load_career_processed_data()

        # groupby researchers
        print("grouping by researcher")
        self.career_data_exploded = (
            self.career_data_processed[
                [
                    "dimensions_researcher_id",
                    "RCR",
                    "dimensions_publication_id",
                    "date",
                    "funder_DR",
                    "funder_crick",
                    "funder_NIHR",
                    "funder_MRC",
                    "funder_wellcome",
                    "author_position",
                    "pub_FOR",
                    "grant_FOR",
                    "pub_FOR_super",
                    "grant_FOR_super",
                    "grant_title",
                    "reference",
                    "DR_scheme",
                    "funding_amount_usd",
                    "grant_start_date",
                    "RCR_log",
                    "RCR_log_above_threshold"
                ]
            ]
            .groupby(by="dimensions_researcher_id", as_index=False)
            .agg(list)
        )
        print(self.career_data_exploded.keys())
        
        # funder relationship booleans to the researcher
        self.career_data_exploded["one_or_more_DR_pubs"] = self.career_data_exploded[
            "funder_DR"
        ].progress_apply(lambda x: any(x))
        self.career_data_exploded["one_or_more_Crick_pubs"] = self.career_data_exploded[
            "funder_crick"
        ].progress_apply(lambda x: any(x))
        self.career_data_exploded[
            "one_or_more_wellcome_pubs"
        ] = self.career_data_exploded["funder_wellcome"].progress_apply(
            lambda x: any(x)
        )
        self.career_data_exploded["one_or_more_NIHR_pubs"] = self.career_data_exploded[
            "funder_NIHR"
        ].progress_apply(lambda x: any(x))
        self.career_data_exploded["one_or_more_MRC_pubs"] = self.career_data_exploded[
            "funder_MRC"
        ].progress_apply(lambda x: any(x))

        # find main FOR
        def most_frequent(input_list):
            if len(input_list) > 0:
                return max(set(input_list), key=input_list.count)
            else:
                return None

        self.career_data_exploded["pub_FOR_super_list"] = self.career_data_exploded[
            "pub_FOR_super"
        ].progress_apply(
            lambda x: [z for y in list(eval(str(x))) for z in eval(str(y))]
        )
        self.career_data_exploded["pub_FOR_super_main"] = self.career_data_exploded[
            "pub_FOR_super_list"
        ].progress_apply(lambda x: most_frequent(x))
        self.career_data_exploded["grant_FOR_super_list"] = self.career_data_exploded[
            "grant_FOR_super"
        ].progress_apply(
            lambda x: [z for y in list(eval(str(x))) for z in eval(str(y))]
        )
        self.career_data_exploded["grant_FOR_super_main"] = self.career_data_exploded[
            "grant_FOR_super_list"
        ].progress_apply(lambda x: most_frequent(x))

        # make FOR groups into a set
        self.career_data_exploded["pub_FOR_super_set"] = self.career_data_exploded[
            "pub_FOR_super"
        ].progress_apply(lambda x: set(x))
        self.career_data_exploded["grant_FOR_super_set"] = self.career_data_exploded[
            "pub_FOR_super"
        ].progress_apply(lambda x: set(x))

        # calculate the time since first pub
        self.career_data_exploded["max_time_since_first_pub"] = self.career_data_exploded[
            "date"
        ].progress_apply(lambda x: (max(x) - min(x)).days / 365.25)

        # calculate the time since first pub
        self.career_data_exploded["time_since_first_pub"] = self.career_data_exploded[
            "date"
        ].progress_apply(lambda x: [(y - min(x)).days / 365.25 for y in x])


        # Create a mapping between 'dates' and 'author_position'
        date_position_mapping = self.career_data_exploded.apply(
            lambda row: list(zip(row["date"], row["author_position"])), axis=1
        )

        # Sort the mapping by 'dates'
        date_position_mapping = date_position_mapping.apply(
            lambda x: sorted(x, key=lambda item: item[0])
        )

        # Extract the sorted 'dates' and 'author_position'
        sorted_dates = date_position_mapping.apply(lambda x: [item[0] for item in x])
        sorted_author_position = date_position_mapping.apply(
            lambda x: [item[1] for item in x]
        )

        # Update the 'author_position' column in the DataFrame
        self.career_data_exploded["sorted_author_position"] = sorted_author_position
        self.career_data_exploded["sorted_dates"] = sorted_dates

        # Iterate through rows and calculate the years between 'first' and 'last' author positions
        for index, row in tqdm(
            self.career_data_exploded.iterrows(),
            desc="calculating time between first and last pub",
        ):
            if "first" in row["sorted_author_position"]:
                first_index = row["sorted_author_position"].index("first")
            else:
                first_index = 0
            if "last" in row["sorted_author_position"]:
                last_index = row["sorted_author_position"].index("last")
            else:
                last_index = first_index

            if first_index > last_index:
                first_index = 0
                last_index = first_index

            first_date = row["sorted_dates"][first_index]
            last_date = row["sorted_dates"][last_index]
            # first_date = career.career_data_exploded.to_datetime(first_date)
            # last_date = career.career_data_exploded.to_datetime(last_date)
            years_between = (
                last_date - first_date
            ).days / 365.25  # 365.25 days in a year

            if years_between == 0:
                years_between = None
            self.career_data_exploded.at[
                index, "years_between_first_last"
            ] = years_between

        # calculating RCR metrics
        self.career_data_exploded["RCR_median"] = self.career_data_exploded[
            "RCR"
        ].progress_apply(lambda x: np.nanmedian(x))

        # save to s3
        s3 = boto3.client("s3")
        self.career_data_exploded.to_csv("career_data_exploded.csv", index=False)
        s3.upload_file(
            "career_data_exploded.csv",
            self.bucket,
            self.researchers_exploded_path + ".csv",
        )
