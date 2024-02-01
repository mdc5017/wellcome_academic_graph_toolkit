import pandas as pd
import boto3
from io import BytesIO
import time

import awswrangler as wr
from multiprocessing import Pool, cpu_count
import time
from wag_toolkit.diversity import IDR
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from wag_toolkit.utils import save_to_s3, read_from_s3


def get_ids(fname):
    """Read file containing dimension linked grants and pubs.

    Args:
        fname(str): location of file 
    """

    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket="datalabs-data", Key=fname)
    global dr_grants
    dr_grants = pd.read_excel(BytesIO(obj["Body"].read()), engine="openpyxl")
    grant_ids = list(dr_grants["grant_id"].dropna().unique())
    pub_ids = list(dr_grants["id"].dropna().unique())
    s3.close()
    return grant_ids, pub_ids

def calculate_diversity(
                        pub_ids,
                        grant_ids=None,
                        dim='grantees_fields',
                        S3_OUTPUT_FOLDER="",
                        parallel=True,
                        weighted=None,
                        ):
    """Call parallelisation for diversity calculation and 
    process parallel outputs to one.

    Args:
        pub_ids(list): List of publication IDs.
        grant_ids(list): List of grant IDS.
        dim(str): Grantee, integration or iiffusion diversity.
        S3_OUTPUT_FOLDER(str): Output folder location.
        parallel(Bool): Whether to utilise multiple cpu cores.
        weighted(bool): Whether to weight by field similarity.
    """

    t0 = time.time()
    print(f"Calculating Diversity: {dim}")
    if dim == "grantees_fields":
        if parallel:
            parallel_diversity(grant_ids, dim, S3_OUTPUT_FOLDER, weighted)
            df = process_parallel_files(dim, S3_OUTPUT_FOLDER)
        else:
            get_metrics(grant_ids, -1, dim, S3_OUTPUT_FOLDER, weighted)
    else:
        if parallel:
            parallel_diversity(pub_ids, dim, S3_OUTPUT_FOLDER, weighted)
            df = process_parallel_files(dim, S3_OUTPUT_FOLDER)
        else:
            get_metrics(pub_ids, -1, dim, S3_OUTPUT_FOLDER, weighted)

    print(f"Completed {dim} similarity calculations in %s seconds" % str(time.time() - t0))
    return df

def parallel_diversity(ids, 
                       dimension="grantee_fields", 
                       S3_OUTPUT_FOLDER="", 
                       weighted=None
                       ):
    """Thread IDs and get_metrics function to multiple CPU cores.

    Args:
        ids(list): publication or grant IDs.
        dimension(str): function of IDR class to call.
        S3_OUTPUT_FOLDER(str): Output folder location.
        weighted(bool): Whether to weight by field similarity.
    """
    ncpus = cpu_count() - 1
    N = len(ids)
    step = int(N / ncpus)

    print(f"Parallelising across {ncpus} cpus")
    with Pool(ncpus) as p:
        p.starmap(
            get_metrics,
            [
                (ids[i : i + step], i, dimension, S3_OUTPUT_FOLDER, weighted)
                for i in range(0, N, step)
            ],
        )
    return

def get_metrics(
                subset,
                i,
                dimension="grantees_fields",
                S3_OUTPUT_FOLDER="funding_impact_measures/idr/dr",
                weighted=None):
    """Call IDR toolkit to calculate diversity metrics.

    Args:
        subset(list): set of publication or grant IDs.
        i(int): index of subset within list.
        dimension(str): function of IDR class to call.
        S3_OUTPUT_FOLDER(str): Output folder location.
        weighted(bool): Whether to weight by field similarity.
    """

    idr = IDR(s3_path=S3_OUTPUT_FOLDER, weighted=weighted)
    idr = getattr(idr, dimension)
    df = idr(subset, max_chunk_size=100)
    save_to_s3(df, fname=f"{S3_OUTPUT_FOLDER}/parallel_files/{dimension}_{i}.csv")
    return

def process_parallel_files(dimension, S3_OUTPUT_FOLDER):
    """Aggregate parallel files to single output.
    
    Args:
        dimension(str): which outputs to aggregate.
        S3_OUTPUT_FOLDER(str): Output folder location.
    """

    print(f"Aggregating and merging {dimension} to grants")
    object_path = f"s3://datalabs-data/{S3_OUTPUT_FOLDER}/parallel_files/{dimension}_*"
    s3_objects = wr.s3.list_objects(path=object_path)
    df = wr.s3.read_csv(s3_objects, use_threads=True)
    if dimension != "grantees_fields":
        # merge to original dimensions pub/grant linkage
        df = df.merge(
            dr_grants[["grant_id", "id"]],
            left_on="p.dimensions_publication_id",
            right_on="id",
        )
    save_to_s3(df, fname=f"{S3_OUTPUT_FOLDER}/{dimension}.csv")
    return df


def cosine_matrix(df, S3_OUTPUT_FOLDER):
    """Calculate cosine similarity from reference list.

    Args:
        df(pd.DataFrame): knowledge integration matrix.
        S3_OUTPUT_FOLDER(str): Output folder location.
    """
    
    print("Calculating cosine similarity")
    idr = IDR()
    try:
        df["super_group_counts"] = df["super_group_counts"].apply(
            lambda x: dict(eval(x))
        )
    except:
        pass
    tally = pd.DataFrame.from_records(
        list(df["super_group_counts"].values), columns=idr.super_groups
    ).fillna(0)
    S = pd.DataFrame(cosine_similarity(tally.T))
    S.columns = idr.super_groups
    S.index = idr.super_groups
    save_to_s3(S, fname=S3_OUTPUT_FOLDER + "/cosine_similarity.csv")
    return

def citation_matrix(df, S3_OUTPUT_FOLDER):
    """Calculate citation similarity from reference list.

    Args:
        df(pd.DataFrame): knowledge integration matrix.
        S3_OUTPUT_FOLDER(str): Output folder location.
    """
    
    print("Calculating citation similarity")
    idr = IDR()
    try:
        df["pub_fields"] = df["pub_fields"].apply(lambda x: dict(eval(x)))
        df["super_group_counts"] = df["super_group_counts"].apply(
            lambda x: dict(eval(x))
        )
    except:
        pass
    df_input = pd.DataFrame.from_records(
        list(df["pub_fields"].values), columns=idr.super_groups
    ).fillna(0)
    df_output = pd.DataFrame.from_records(
        list(df["super_group_counts"].values), columns=idr.super_groups
    ).fillna(0)

    assert df_input.columns.equals(df_output.columns)
    assert len(df_input) == len(df_output)

    super_groups = idr.super_groups
    N = len(super_groups)
    D = df_input.shape[0]
    S = np.zeros((N, N))
    O = df_output.values
    for i, field in enumerate(super_groups):
        idx = df_input[field].values
        I = np.tile(idx, N).reshape(N, D)
        S[i, :] += np.multiply(I.T, O).sum(axis=0)

    S = pd.DataFrame(S)
    S = S.div(S.sum(axis=1), axis=0).fillna(0)
    S.columns = idr.super_groups
    S.index = idr.super_groups
    save_to_s3(S, fname=S3_OUTPUT_FOLDER + "/citation_similarity.csv")
    return