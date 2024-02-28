import numpy as np
from wag_toolkit.utils import save_to_s3, read_from_s3


def aggregate_grant_level(S3_OUTPUT_FOLDER):
    """Clean and aggregate team, output and impact data to grant level.

    Args:
        S3_OUTPUT_FOLDER(str): location of input and output files.
    """

    # TEAM ANALYSIS
    print("Aggregating and cleaning team diversity data to grant level...")
    teams = read_from_s3(S3_OUTPUT_FOLDER + "/grantees_fields.csv")

    # remove researchers with less than 20 publications
    teams = teams[teams["no_pubs"] >= 20]
    teams["top_supergroups"] = teams["top_supergroups"].apply(lambda x: eval(x))
    mean = teams["rs_cosine"].mean()

    # give researcher one or two fields depending on diversity
    teams["researcher_field"] = teams.apply(
        lambda x: x.top_supergroups if x.rs_cosine >= mean else x.top_supergroups[0],
        axis=1,
    )
    teams["top_field"] = teams.apply(lambda x: x.top_supergroups[0], axis=1)

    # group by grant
    grant_teams = teams[["rs_cosine", "id(g)"]].groupby("id(g)").mean()
    grant_teams["std"] = (
        teams[["rs_cosine", "id(g)"]].groupby("id(g)").std()["rs_cosine"]
    )
    grant_teams["team_members"] = (
        teams[["rs_cosine", "id(g)"]].groupby("id(g)").count()["rs_cosine"]
    )
    grant_teams["id(g)"] = grant_teams.index
    grant_teams.index = np.arange(0, grant_teams.shape[0])
    grant_teams = grant_teams.merge(
        teams[["g.dimensions_grant_id", "g.original_source_id", "id(g)"]],
        on="id(g)",
        how="left",
    ).drop_duplicates()
    grant_teams["researcher_fields"] = (
        teams[["id(g)", "researcher_field"]]
        .groupby("id(g)")["researcher_field"]
        .apply(list)
        .values
    )
    grant_teams["top_fields"] = (
        teams[["id(g)", "top_field"]].groupby("id(g)")["top_field"].apply(list).values
    )
    grant_teams["g.start_date"] = (
        teams[["id(g)", "g.start_date"]].groupby("id(g)").first()["g.start_date"].values
    )
    grant_teams.columns = [
        "team_diversity",
        "team_std_diversity",
        "no_team_members",
        "id(g)",
        "g.dimensions_grant_id",
        "g.original_source_id",
        "researcher_fields",
        "top_fields",
        "g.start_date",
    ]

    grant_teams["no_team_fields"] = grant_teams["top_fields"].apply(
        lambda x: len(list(set(x)))
    )

    grant_teams["idr_types"] = grant_teams.apply(
        lambda x: label_idr_types(x, mean), axis=1
    )

    save_to_s3(grant_teams, fname=S3_OUTPUT_FOLDER + "/grantees_field_bygrant.csv")

    # OUTPUT TO GRANT ANALYSIS
    print("Aggregating and cleaning output diversity data to grant level...")
    outputs = read_from_s3(S3_OUTPUT_FOLDER + "/knowledge_integration.csv")

    # remove outputs with less than 8 references
    outputs = outputs[outputs["no_refs"] >= 8]
    outputs["pub_fields"] = outputs["pub_fields"].apply(
        lambda x: [i[0] for i in eval(x)]
    )

    # group by grant
    grant_outputs = outputs[["rs_cosine", "grant_id"]].groupby("grant_id").mean()
    grant_outputs["std"] = (
        outputs[["rs_cosine", "grant_id"]].groupby("grant_id").std()["rs_cosine"]
    )
    grant_outputs["no_pubs"] = (
        outputs[["rs_cosine", "grant_id"]].groupby("grant_id").count()["rs_cosine"]
    )
    grant_outputs["grant_id"] = grant_outputs.index
    grant_outputs.index = np.arange(0, grant_outputs.shape[0])
    grant_outputs["pub_fields"] = (
        outputs[["grant_id", "pub_fields"]]
        .groupby("grant_id")["pub_fields"]
        .apply(list)
        .values
    )
    grant_outputs.columns = [
        "output_diversity",
        "output_std_diversity",
        "no_pubs",
        "grant_id",
        "pub_fields",
    ]
    grant_outputs = grant_outputs.merge(
        teams[["g.dimensions_grant_id", "g.start_date"]].drop_duplicates(),
        left_on="grant_id",
        right_on="g.dimensions_grant_id",
        how="left",
    ).dropna()

    save_to_s3(
        grant_outputs, fname=S3_OUTPUT_FOLDER + "/knowledge_integration_bygrant.csv"
    )

    # IMPACT TO GRANT ANALYSIS
    print("Aggregating and cleaning citation diversity data to grant level...")
    impact = read_from_s3(S3_OUTPUT_FOLDER + "/knowledge_diffusion.csv")

    # remove publications  with less than 10 citations
    impact = impact[impact["no_cite"] >= 10]
    impact["pub_fields"] = impact["pub_fields"].apply(
        lambda x: None if x is np.nan else [i[0] for i in eval(x)]
    )
    grant_impact = impact[["rs_cosine", "grant_id"]].groupby("grant_id").mean()
    grant_impact["std"] = (
        impact[["rs_cosine", "grant_id"]].groupby("grant_id").std()["rs_cosine"]
    )
    grant_impact["no_pubs"] = (
        impact[["rs_cosine", "grant_id"]].groupby("grant_id").count()["rs_cosine"]
    )
    grant_impact["total_citations"] = (
        impact[["no_cite", "grant_id"]].groupby("grant_id").sum()["no_cite"]
    )
    grant_impact["grant_id"] = grant_impact.index
    grant_impact.index = np.arange(0, grant_impact.shape[0])
    grant_impact["pub_fields"] = (
        impact[["grant_id", "pub_fields"]]
        .groupby("grant_id")["pub_fields"]
        .apply(list)
        .values
    )
    grant_impact.columns = [
        "impact_diversity",
        "impact_std_diversity",
        "no_pubs",
        "total_citation",
        "grant_id",
        "pub_fields",
    ]

    grant_impact = grant_impact.merge(
        teams[["g.dimensions_grant_id", "g.start_date"]].drop_duplicates(),
        left_on="grant_id",
        right_on="g.dimensions_grant_id",
        how="left",
    ).dropna()

    save_to_s3(
        grant_impact, fname=S3_OUTPUT_FOLDER + "/knowledge_diffusion_bygrant.csv"
    )

    print("Merging team, output and citation diversity data to grant level...")
    merged = grant_impact.merge(grant_outputs, on="grant_id").merge(
        grant_teams, left_on="grant_id", right_on="g.dimensions_grant_id"
    )
    merged["no_team_fields"] = merged["top_fields"].apply(lambda x: len(list(set(x))))
    merged["idr_types"] = merged.apply(
        lambda x: label_idr_types(x, merged["team_diversity"].mean()), axis=1
    )

    save_to_s3(merged, fname=S3_OUTPUT_FOLDER + "/all_bygrant.csv")
    return print("Processed all input files to grant-level")


def label_idr_types(df, mean):
    """Tag grants with type of IDR based on diversity and team members.

    Args:
        df(pd.DataFrame): team diversity dataframe.
        mean(float64): average team diversity for threshold.
    """

    if df.no_team_members == 1 and df.team_diversity < mean:
        name = "Discipline Expert"
    elif df.no_team_members == 1 and df.team_diversity >= mean:
        name = "Individual breaking down siloes"
    elif (
        df.no_team_members != 1 and df.no_team_fields == 1 and df.team_diversity < mean
    ):
        name = "Discipline Experts"
    elif (
        df.no_team_members != 1 and df.no_team_fields == 1 and df.team_diversity >= mean
    ):
        name = "Teams breaking down siloes"
    elif (
        df.no_team_members != 1 and df.no_team_fields == 2 and df.team_diversity < mean
    ):
        name = "Cross-disciplinary"
    elif (
        df.no_team_members != 1 and df.no_team_fields == 2 and df.team_diversity >= mean
    ):
        name = "Inter-disciplinary"
    elif (
        df.no_team_members != 1 and df.no_team_fields >= 3 and df.team_diversity < mean
    ):
        name = "Multi-disciplinary"
    elif (
        df.no_team_members != 1 and df.no_team_fields >= 3 and df.team_diversity >= mean
    ):
        name = "Inter-disciplinary"
    else:
        name = "Border-case"
    return name
