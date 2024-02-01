import pandas as pd
import numpy as np
import plotly.express as px
import boto3
import gzip
from wag_toolkit.diversity import IDR
from io import StringIO, BytesIO
from .process import label_idr_types
from wag_toolkit.utils import Neo4j, read_from_s3


def idr_types(S3_OUTPUT_FOLDER, scheme_mapping, award_mapping):
    """Visualisation of grants by number of grantees and diversity.

    Args:
        S3_OUTPUT_FOLDER(str): Output folder location which will also be used as save_path.
        scheme_mapping(str): Location of metadata for grants by scheme.
        award_mapping(str): Location of grant award metadata.
    """

    merged = read_from_s3(S3_OUTPUT_FOLDER + "/all_bygrant.csv")

    merged["xaxis"] = merged.apply(lambda x: classify_xaxis(x), axis=1)
    merged["jittered"] = merged["xaxis"] + np.random.uniform(
        -0.485, 0.485, merged.shape[0]
    )

    scheme = pd.read_csv(scheme_mapping)
    merged = merged.merge(scheme, left_on="g.original_source_id", right_on="Reference")

    awards = pd.read_csv(award_mapping)
    merged = merged.merge(
        awards[
            ["Reference", "Title", "Master Grant Type Name", "Lead Applicant Full Name"]
        ],
        right_on="Reference",
        left_on="g.original_source_id",
    )

    fig = px.scatter(
        merged,
        x="jittered",
        y="team_diversity",
        color="output_diversity",
        symbol="Open mode / Directed",
        #  animation_frame="year",
        hover_data=[
            "team_std_diversity",
            "Title",
            "Lead Applicant Full Name",
            "no_team_members",
            "no_team_fields",
            "researcher_fields",
            "no_pubs_x",
        ],
        labels={
            "team_std_diversity": "Std. Team Diversity",
            "jittered": "Researcher(s) Number of Fields",
            "team_diversity": "Mean Team Diversity",
            "no_pubs_x": "Publications from Grant",
        },
        title="Scatterplot of Types of Research Teams based on Team Diversity and Number of Members",
    )

    fig.add_vline(x=1.5, line_dash="dash", line_color="black")
    fig.add_vline(x=2.5, line_dash="dash", line_color="black")
    fig.add_vline(x=3.5, line_dash="dash", line_color="black")
    fig.add_vline(x=4.5, line_dash="dash", line_color="grey")
    fig.add_vline(x=5.5, line_dash="dash", line_color="grey")
    fig.add_vline(x=0.5, line_dash="dash", line_color="black")
    fig.add_hline(
        y=merged["team_diversity"].mean(), line_dash="dash", line_color="black"
    )  # vertical line at the mean of jittered category

    custom_labels = {
        1: "Single Researcher",
        2: "Teams w/ Single Field",
        3: "Teams w/ 2 Fields",
        4: "Teams w/ 3 Fields",
        5: "Teams w/ 4 Fields",
        6: "Teams w/ 5 Fields",
        7: "Teams w/ 6 Fields",
        8: "Teams w/ 7 Fields",
    }

    fig.update_xaxes(tickvals=np.arange(1, 7, 1), ticktext=list(custom_labels.values()))
    fig.update_layout(coloraxis=dict(colorbar=dict(orientation="h", y=-0.15)))
    fig.update_coloraxes(
        colorbar_title_text="Integration Diversity", colorbar_title_font_size=24
    )

    fig.add_annotation(
        x=0.7, y=0.05, text="Discpline Expert", showarrow=True, arrowhead=1
    )

    fig.add_annotation(
        x=0.7,
        y=0.55,
        text="Individuals breaking down Siloes",
        showarrow=True,
        arrowhead=1,
    )

    fig.add_annotation(
        x=1.7, y=0.25, text="Discpline Experts", showarrow=True, arrowhead=1
    )

    fig.add_annotation(
        x=1.9, y=0.35, text="Teams breaking down Siloes", showarrow=True, arrowhead=1
    )

    fig.add_annotation(
        x=2.9, y=0.17, text="Cross-disciplinary", showarrow=True, arrowhead=1
    )

    fig.add_annotation(
        x=2.7, y=0.45, text="Inter-disciplinary", showarrow=True, arrowhead=1
    )

    fig.add_annotation(
        x=3.9, y=0.12, text="Multi-discplinary", showarrow=True, arrowhead=1
    )

    fig.add_annotation(
        x=3.7, y=0.40, text="Inter-discplinary", showarrow=True, arrowhead=1
    )

    fig.add_annotation(
        x=merged[merged["grant_id"] == "grant.10029634"]["jittered"].values[0],
        y=merged[merged["grant_id"] == "grant.10029634"]["team_diversity"].values[0],
        text="x",
    )

    fig.add_annotation(
        x=merged[merged["grant_id"] == "grant.4579821"]["jittered"].values[0],
        y=merged[merged["grant_id"] == "grant.4579821"]["team_diversity"].values[0],
        text="x",
    )

    title_font_size = 24
    axis_label_font_size = 24
    tick_label_font_size = 24
    legend_font_size = 24
    annotation_font_size = 24

    fig.update_layout(
        title_font_size=title_font_size,
        xaxis_title_font_size=axis_label_font_size,
        yaxis_title_font_size=axis_label_font_size,
        xaxis_tickfont_size=tick_label_font_size,
        yaxis_tickfont_size=tick_label_font_size,
        legend_font_size=legend_font_size,
    )

    hover_label_font_size = 16

    fig.update_traces(hoverlabel=dict(font_size=hover_label_font_size))

    fig.update_annotations(font_size=annotation_font_size)

    fig.write_html("./idr/vis/team_field_diversity.html")


def classify_xaxis(df):
    """X-axis formatting for idr types visualisation.

    Args:
        df(pd.DataFrame): team dataframe.
    """

    if df.no_team_members == 1:
        y = 1
    elif df.no_team_members != 1 and df.no_team_fields == 1:
        y = 2
    else:
        y = df.no_team_fields + 1
    return y


def unique_fields(row):
    fields = []
    for item in row:
        if type(item) == str:
            fields.append(item)
        elif type(item) == tuple:
            for j in item:
                fields.append(j)
    return fields


def topic_treemap(S3_OUTPUT_FOLDER, award_mapping):
    """Visualisation of topics and nested IDR types, researcher fields and grants.

    Args:
        S3_OUTPUT_FOLDER(str): Output folder location which will also be used as save_path.
        award_mapping(str): Location of grant award metadata.
    """

    outputs_merged, both = merge_topics(S3_OUTPUT_FOLDER, award_mapping)

    counts = (
        outputs_merged[["idr_types", "name", "rs_cosine", "unique_fields", "Title"]]
        .groupby(["idr_types", "name", "unique_fields", "Title"])
        .count()
    )

    counts["idr_types"] = [counts.index[i][0] for i in range(counts.shape[0])]
    counts["topic"] = [counts.index[i][1] for i in range(counts.shape[0])]
    counts["team_type"] = [counts.index[i][2] for i in range(counts.shape[0])]
    counts["grant"] = [counts.index[i][3] for i in range(counts.shape[0])]
    counts.index = np.arange(counts.shape[0])
    counts.columns = ["counts", "idr_types", "name", "team_type", "grant"]

    div = (
        outputs_merged[["idr_types", "name", "rs_cosine", "unique_fields", "Title"]]
        .groupby(["idr_types", "name", "unique_fields", "Title"])
        .median()
    )
    counts["integration_diversity"] = div["rs_cosine"].values

    counts = pd.merge(counts, both, on="name", how="left")

    counts.columns = [
        "counts",
        "idr_types",
        "topic",
        "team_type",
        "grant",
        "diversity",
        "topic no.",
        "parent1",
        "parent2",
        "parent3",
        "keywords",
    ]

    sub = counts[counts["counts"] > 1]
    fig = px.treemap(
        sub,
        path=[px.Constant("Topics"), "topic", "idr_types", "team_type", "grant"],
        values="counts",
        color="diversity",
        hover_data={"topic": "topic"},
        color_continuous_scale="tropic",
        color_continuous_midpoint=np.average(counts["diversity"]),
        title="Treemap of Publication Topics -> IDR Team Types -> Researcher Field Disciplines > Grants, coloured by Integration Diversity<br>"
        + "<sup>Example: Genomic & Genetic Research makes up the largest portion of the portfolio. A large portion of this work is driven by individuals breaking down siloes<br>"
        + "and Interdisciplinary teams, with the most diverse outputs arising from team grants such as STRADL, NextGenScot & GWAS.</sup>",
    )

    fig.update_layout(margin=dict(t=150, l=25, r=25, b=25))
    fig.update_traces(
        hovertemplate="<b>Group</b>: %{label}<br>"
        + "<b>counts</b>: %{value}<br>"
        + "<b>parent</b>: %{parent}<br>"
        + "<b>integration diversity</b>: %{color}"
    )
    fig.update_coloraxes(
        colorbar_title_text="Integration Diversity", colorbar_title_font_size=18
    )

    fig.update_traces(hoverlabel=dict(font_size=20))
    fig.write_html("./idr/vis/topic_treemap.html")
    return


def merge_topics(S3_OUTPUT_FOLDER, award_mapping):
    """Merge topics to publications.

    Args:
        S3_OUTPUT_FOLDER(str): Output folder location which will also be used as save_path.
        award_mapping(str): Location of grant award metadata.
    """

    s3 = boto3.client("s3")
    obj = s3.get_object(
        Bucket="datalabs-data",
        Key="funding_impact_measures/topics/tableau/topics_per_doc.csv.gz",
    )
    f = gzip.open(BytesIO(obj["Body"].read()), "rb")
    file_content = f.read()
    s = str(file_content, "utf-8")
    data = StringIO(s)
    topics = pd.read_csv(data)

    # read hierarchies
    obj = s3.get_object(
        Bucket="datalabs-data",
        Key="funding_impact_measures/topics/tableau/hierarchy.csv.gz",
    )
    f = gzip.open(BytesIO(obj["Body"].read()), "rb")
    file_content = f.read()
    s = str(file_content, "utf-8")
    data = StringIO(s)
    hierarchy = pd.read_csv(data)

    # read hierarchies
    obj = s3.get_object(
        Bucket="datalabs-data",
        Key="funding_impact_measures/topics/tableau/topic_info.csv.gz",
    )
    f = gzip.open(BytesIO(obj["Body"].read()), "rb")
    file_content = f.read()
    s = str(file_content, "utf-8")
    data = StringIO(s)
    info = pd.read_csv(data)

    both = hierarchy.merge(info)
    outputs = read_from_s3(S3_OUTPUT_FOLDER + "/knowledge_integration.csv")

    outputs = outputs.merge(
        topics[["dimensions_publication_id", "topic"]],
        left_on="p.dimensions_publication_id",
        right_on="dimensions_publication_id",
    )
    outputs = outputs.merge(both, on="topic")

    merged = read_from_s3(S3_OUTPUT_FOLDER + "/all_bygrant.csv")
    awards = pd.read_csv(award_mapping)
    merged = merged.merge(
        awards[
            ["Reference", "Title", "Master Grant Type Name", "Lead Applicant Full Name"]
        ],
        right_on="Reference",
        left_on="g.original_source_id",
    )

    merged["no_team_fields"] = merged["top_fields"].apply(
        lambda x: len(list(set(eval(x))))
    )
    merged["idr_types"] = merged.apply(
        lambda x: label_idr_types(x, merged["team_diversity"].mean()), axis=1
    )
    merged["unique_fields"] = merged["researcher_fields"].apply(
        lambda x: str(set(unique_fields(eval(x))))
    )

    outputs_merged = outputs.merge(
        merged[["g.dimensions_grant_id", "idr_types", "Title", "unique_fields"]],
        right_on="g.dimensions_grant_id",
        left_on="grant_id",
    )
    return outputs_merged, both


def topic_diversity(S3_OUTPUT_FOLDER, award_mapping):
    """Visualisation of topic diversity scattered by diversity deviation.

    Args:
        S3_OUTPUT_FOLDER(str): Output folder location which will also be used as save_path.
        award_mapping(str): Location of grant award metadata.
    """

    outputs_merged, both = merge_topics(S3_OUTPUT_FOLDER, award_mapping)
    grouped = outputs_merged[["name", "rs_cosine"]].groupby("name").median()

    grouped["std"] = (
        outputs_merged[["name", "rs_cosine"]].groupby("name").std()["rs_cosine"]
    )
    grouped["count"] = outputs_merged[["name", "rs_cosine"]].groupby("name").count()
    grouped["topic"] = grouped.index
    grouped["parent"] = (
        outputs_merged[["name", "parent"]].groupby("name").max()["parent"]
    )

    fig = px.scatter(
        grouped,
        x="rs_cosine",
        y="std",
        size="count",
        hover_data=["topic"],
        color="topic",
        labels={
            "rs_cosine": "Integration Diversity",
            "std": "Integration Diversity Standard Deviation",
            "topic": "Topic",
        },
        title="Scatterplot of Topic Interation Diversity by Deviation<br>"
        + "<sup>Topics are shown as scatter points with their size proportional to the number of times the topic appears in the portfolio.<br>"
        + "Topics are scattered by average integration diversity and the standard deviation of integration diversity.<br>"
        + "Higher deviation (y-axis) represents topics that with varying levels of knowledge integration.<br></sup><br>",
        size_max=55,
    )

    fig.add_vline(x=grouped["rs_cosine"].mean(), line_dash="dash", line_color="black")
    fig.add_hline(
        y=grouped["std"].mean(), line_dash="dash", line_color="black"
    )  # vertical line at the mean of jittered category
    fig.update_layout(margin=dict(l=20, r=20, t=150, b=20))

    fig.write_html("./idr/vis/topic_diversity.html")
    return


def sub_fields(S3_OUTPUT_FOLDER):
    """Get unique sub-fields from publication.

    Args:
        S3_OUTPUT_FOLDER(str): Output folder location which will also be used as save_path.
    """

    outputs = read_from_s3(S3_OUTPUT_FOLDER + "/knowledge_integration.csv")
    idr = IDR(s3_path=None, weighted=False)
    super_groups = idr.super_groups
    all_fields = outputs["p.for"].apply(lambda x: idr.format_fields([x])[0])
    outputs["sub_fields"] = all_fields.apply(
        lambda x: [i for i in x if i not in super_groups]
    )
    outputs["super_fields"] = all_fields.apply(
        lambda x: [i for i in x if i in super_groups]
    )
    return outputs


def subfield_diversity(S3_OUTPUT_FOLDER):
    """Visualisation of topic diversity scattered by diversity deviation.

    Args:
        S3_OUTPUT_FOLDER(str): Output folder location which will also be used as save_path.
    """

    outputs = sub_fields(S3_OUTPUT_FOLDER)

    sub_outputs = outputs[["rs_cosine", "sub_fields", "super_fields"]]
    sub_outputs = sub_outputs.explode("sub_fields")

    grouped = sub_outputs[["sub_fields", "rs_cosine"]].groupby("sub_fields").median()
    idr = IDR(s3_path=None, weighted=False)
    grouped["std"] = (
        sub_outputs[["sub_fields", "rs_cosine"]]
        .groupby("sub_fields")
        .std()["rs_cosine"]
    )
    grouped["count"] = (
        sub_outputs[["sub_fields", "rs_cosine"]].groupby("sub_fields").count()
    )
    grouped["Sub Field"] = grouped.index
    grouped["Super Group"] = grouped["Sub Field"].apply(
        lambda x: str(idr.convert_to_supergroup([[x]])[0])
    )

    fig = px.scatter(
        grouped,
        x="rs_cosine",
        y="std",
        size="count",
        hover_data=["Super Group"],
        color="Sub Field",
        labels={
            "rs_cosine": "Integration Diversity",
            "std": "Integration Diversity Standard Deviation",
        },
        title="Scatterplot of Sub Field Integration Diversity by Deviation<br>"
        + "<sup>Sub Fields are shown as scatter points with their size proportional to the number of times the sub field appears in the portfolio.<br>"
        + "Sub Fields are scattered by average integration diversity and the standard deviation of integration diversity.<br>"
        + "Higher deviation (y-axis) represents fields that with varying levels of knowledge integration.<br></sup><br>",
        size_max=75,
    )
    fig.add_vline(
        x=sub_outputs["rs_cosine"].mean(), line_dash="dash", line_color="black"
    )
    fig.add_hline(y=grouped["std"].mean(), line_dash="dash", line_color="black")
    fig.update_layout(margin=dict(l=20, r=20, t=150, b=20))
    fig.write_html("./idr/vis/subfield_diversity.html")
    return


def subfield_treemap(S3_OUTPUT_FOLDER, award_mapping):
    """Visualisation of sub-fields and nested IDR types, researcher fields and grants.

    Args:
        S3_OUTPUT_FOLDER(str): Output folder location which will also be used as save_path.
        award_mapping(str): Location of grant award metadata.
    """

    outputs = sub_fields(S3_OUTPUT_FOLDER)

    sub_outputs = outputs[
        [
            "rs_cosine",
            "sub_fields",
            "super_fields",
            "grant_id",
            "p.dimensions_publication_id",
        ]
    ]
    sub_outputs = sub_outputs.explode("sub_fields")

    merged = read_from_s3(S3_OUTPUT_FOLDER + "/all_bygrant.csv")
    awards = pd.read_csv(award_mapping)
    merged = merged.merge(
        awards[
            ["Reference", "Title", "Master Grant Type Name", "Lead Applicant Full Name"]
        ],
        right_on="Reference",
        left_on="g.original_source_id",
    )

    merged["no_team_fields"] = merged["top_fields"].apply(
        lambda x: len(list(set(eval(x))))
    )
    merged["idr_types"] = merged.apply(
        lambda x: label_idr_types(x, merged["team_diversity"].mean()), axis=1
    )
    merged["unique_fields"] = merged["researcher_fields"].apply(
        lambda x: str(set(unique_fields(eval(x))))
    )

    outputs_merged = sub_outputs.merge(
        merged[["g.dimensions_grant_id", "idr_types", "Title", "unique_fields"]],
        right_on="g.dimensions_grant_id",
        left_on="grant_id",
    )

    counts = (
        outputs_merged[
            ["idr_types", "sub_fields", "rs_cosine", "unique_fields", "Title"]
        ]
        .groupby(["idr_types", "sub_fields", "unique_fields", "Title"])
        .count()
    )

    counts["idr_types"] = [counts.index[i][0] for i in range(counts.shape[0])]
    counts["sub_fields"] = [counts.index[i][1] for i in range(counts.shape[0])]
    counts["team_type"] = [counts.index[i][2] for i in range(counts.shape[0])]
    counts["grant"] = [counts.index[i][3] for i in range(counts.shape[0])]
    counts.index = np.arange(counts.shape[0])
    counts.columns = ["counts", "idr_types", "sub_fields", "team_type", "grant"]

    div = (
        outputs_merged[
            ["idr_types", "sub_fields", "rs_cosine", "unique_fields", "Title"]
        ]
        .groupby(["idr_types", "sub_fields", "unique_fields", "Title"])
        .median()
    )
    counts["integration_diversity"] = div["rs_cosine"].values

    sub = counts[counts["counts"] > 1]
    sub = sub[sub["sub_fields"] != ""]
    fig = px.treemap(
        sub,
        path=[
            px.Constant("Sub Field"),
            "sub_fields",
            "idr_types",
            "team_type",
            "grant",
        ],
        values="counts",
        color="integration_diversity",
        hover_data={"sub_fields": "Sub Field"},
        color_continuous_scale="tropic",
        color_continuous_midpoint=np.average(sub["integration_diversity"]),
        title="Treemap of Sub Field -> IDR Team Types -> Researcher Field Disciplines -> Grants, coloured by Integration Diversity<br>"
        + "<sup>Example: Genetics makes up almost 10 percent of the portfolio. A large portion of this work is driven by individuals breaking down siloes<br>"
        + "that mostly span Biological and Biomedical Sciences. The least interdisciplinary work arises from Discipline Experts working in Biological Sciences<br>"
        + "while the most diverse span Psychology and Biomedical Sciences. There are examples of high diversity grants which include Humanties and Ethics such as <br>"
        + "Early Intervention and Moral Development in Child Psychiatry.</sup>",
    )

    fig.update_layout(margin=dict(t=200, l=25, r=25, b=25))
    fig.update_traces(
        hovertemplate="<b>Group</b>: %{label}<br>"
        + "<b>Counts</b>: %{value}<br>"
        + "<b>Parent</b>: %{parent}<br>"
        + "<b>Integration diversity</b>: %{color}"
    )
    fig.update_coloraxes(
        colorbar_title_text="Integration Diversity", colorbar_title_font_size=18
    )

    fig.update_traces(hoverlabel=dict(font_size=16))
    fig.write_html("./idr/vis/subfield_treemap.html")
    return
