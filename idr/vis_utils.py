from html_reports import Report
from wag_toolkit.utils import read_from_s3
import matplotlib.pyplot as plt
import seaborn as sns
import wag_toolkit
import pandas as pd
import numpy as np
from collections import Counter


def summary_reports(S3_OUTPUT_FOLDER, basic=None, diversity=None):
    """Create html report analysis on basic descriptives from teams,
    outputs, citations data, as well as diversity analysis.
    
    Args:
        S3_OUTPUT_FOLDER(str): Output folder location which will also be used as save_path.
        basic(bool): whether to output basic summary report.
        diversity(bool): whether to output diversity summary report.
    """

    global teams, outputs, impact, idr

    teams = read_from_s3(S3_OUTPUT_FOLDER + "/grantees_fields.csv")
    outputs = read_from_s3(S3_OUTPUT_FOLDER + "/knowledge_integration.csv")
    impact = read_from_s3(S3_OUTPUT_FOLDER + "/knowledge_diffusion.csv")
    idr = wag_toolkit.IDR(s3_path=S3_OUTPUT_FOLDER, diversity=True)

    # preprocessing
    outputs["pub_fields"] = outputs["pub_fields"].apply(
        lambda x: [i[0] for i in eval(x)]
    )
    impact["pub_fields"] = impact["pub_fields"].apply(
        lambda x: None if x is np.nan else [i[0] for i in eval(x)]
    )

    if basic:
        print("Creating basic statistics summary report")
        rep1 = Report()
        rep1.add_title(
            "Descriptives Statistics from Portfolio for Teams, Outputs and Impact"
        )
        summary_statistics_teams(rep1)
        summary_statistics_outputs(rep1)
        summary_statistics_impact(rep1)
        rep1.write_report(filename="./vis/summary_statistics_report.html")

    if diversity:
        print("Creating diversity summary report")
        rep2 = Report()
        rep2.add_title("Summary of Diversity Metrics")
        summary_diversity(rep2)

        summary_diversity_teams(rep2)
        summary_diversity_outputs(rep2)
        summary_diversity_impact(rep2)
        rep2.write_report(filename= "./vis/summary_diversity_report.html")

def summary_statistics_teams(rep):
    """"Basic descriptive plots for researchers.
    
    Args:
        rep(html_report): report.
    """

    rep.add_title("Summary Stats for Teams", level=2)

    unique_grants = teams["id(g)"].unique().shape[0]
    unique_researchers = teams["id(r)"].unique().shape[0]

    # totals and averages
    teams["baseline"] = teams["g.start_date"].apply(
        lambda x: "pre" if int(x[:4]) <= 2021 else "post"
    )
    agg = teams[["id(g)", "id(r)", "baseline"]].groupby(["id(g)", "baseline"]).count()
    agg["baseline"] = [i[1] for i in agg.index]
    agg.index = [np.arange(agg.shape[0])]
    baseline_counts = agg.groupby("baseline").count().values

    rep.add_markdown(
        f"There are a total of {unique_grants} unique grants and {unique_researchers} unique researchers."
    )
    rep.add_markdown(
        f"Pre-baseline (all years up until the end of 2021) there were {baseline_counts[1][0]} grants awarded compared to {baseline_counts[0][0]} post baseline."
    )

    # distribution of grantees per grant plot
    sns.set_style("ticks")
    ax = sns.countplot(agg, x="id(r)", hue="baseline")
    ax.bar_label(ax.containers[0], color="blue")
    ax.bar_label(ax.containers[1], color="orange")
    plt.ylabel("Total Frequency")
    plt.xlabel("Team Size")
    plt.title("Histogram for Size of Team per Grant")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    rep.add_markdown(
        f"Researchers have an average of {teams['no_pubs'].mean()} publications prior to being awarded a grant. \
                     Assuming researchers publication field to be the field in which they publish most, \
                     the following charts show the Top and Second Researcher Fields."
    )
    # top field and second top field bar charts
    field_counts = (
        teams.drop_duplicates(subset=["id(r)"])["top_supergroups"]
        .apply(lambda x: eval(x)[0])
        .value_counts()
    )
    plt.bar(field_counts.index, field_counts.values, color="skyblue")
    for index, value in enumerate(field_counts.values):
        plt.text(index, value, str(value), ha="center", va="bottom")
    plt.xlabel("Field")
    plt.ylabel("Number of Researchers")
    plt.title("Top Field of Researchers")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    field_counts = (
        teams.drop_duplicates(subset=["id(r)"])["top_supergroups"]
        .apply(lambda x: eval(x)[1])
        .value_counts()
    )
    plt.bar(field_counts.index, field_counts.values, color="skyblue")
    for index, value in enumerate(field_counts.values):
        plt.text(index, value, str(value), ha="center", va="bottom")
    plt.xlabel("Field")
    plt.ylabel("Number of Researchers")
    plt.title("Second Field of Researchers")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    return

def summary_statistics_outputs(rep):
    """"Basic descriptive plots for publication outputs.
    
    Args:
        rep(html_report): report.
    """

    rep.add_title("Summary Stats for Outputs", level=2)

    # totals and averages
    unique_publications = outputs["p.dimensions_publication_id"].unique().shape[0]
    unique_grants = outputs["grant_id"].unique().shape[0]

    field_counts = outputs.drop_duplicates(subset=["id(p)"])["pub_fields"].apply(
        lambda x: dict(eval(x))
    )
    field_counts = (
        pd.DataFrame.from_records(list(field_counts.values), columns=idr.super_groups)
        .fillna(0)
        .sum(axis=0)
        .sort_values(ascending=False)
    )
    top3 = int(field_counts[:3].sum() / field_counts.sum() * 100)

    agg = outputs[["id(p)", "grant_id"]].groupby("grant_id").count()

    rep.add_markdown(
        f"There are a total of {unique_publications} unique publications from a atotal of {unique_grants} unique grants."
    )
    rep.add_markdown(
        f"The top 3 fields {list(field_counts.index[:3])} make up {top3}% of the portfolio."
    )
    rep.add_markdown(
        f"On average, each grant results in {int(agg.mean().values[0])} publications."
    )

    # total publications per field
    plt.bar(field_counts.index, field_counts.values, color="skyblue")
    for index, value in enumerate(field_counts.values):
        plt.text(index, value, str(int(value)), ha="center", va="bottom")
    plt.xlabel("Field")
    plt.ylabel("Number of Publications")
    plt.title("Publication Tags Total")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    # histogram of publication per grant
    sns.set_style("ticks")
    ax = sns.histplot(agg, x="id(p)")
    plt.ylabel("Total Frequency")
    plt.xlabel("Publications per Grant")
    plt.title("Histogram of Publication Outputs per Grant")
    plt.tight_layout()
    plt.xlim(0, 200)
    plt.draw()
    rep.add_figure()
    plt.clf()
    return

def summary_statistics_impact(rep):
    """"Basic descriptive plots for publication citations.
    
    Args:
        rep(html_report): report.
    """

    rep.add_title("Summary Stats for Impact", level=2)

    # totals and averages
    unique_publications = impact["p.dimensions_publication_id"].unique().shape[0]
    unique_grants = impact["grant_id"].unique().shape[0]
    citations_per_publication = impact.drop_duplicates(subset=["id(p)"])[
        "no_cite"
    ].mean()
    agg = impact[["no_cite", "grant_id"]].groupby("grant_id").sum()

    rep.add_markdown(
        f"There are a total of {unique_publications} unique publications from a total of {unique_grants} unique grants which have citations."
    )
    rep.add_markdown(
        f"Average number of citations across publications is {citations_per_publication}."
    )
    rep.add_markdown(
        f"On average, each grant results in a total of {int(agg.mean().values[0])} citations. This is impacted by the date of publication, since older publications \
                     accrue greater number of citations."
    )
    rep.add_markdown(
        f"The graph below shows the average number of citations per publication per field cumulatively (left), and per year averages across all fields (right)."
    )

    # calculate average citation rates per year after publication
    temporal_citations = impact[["p.date", "COLLECT(c.date)", "pub_fields"]].dropna()
    temporal_citations["pub_year"] = temporal_citations["p.date"].apply(
        lambda x: int(x[:4])
    )
    temporal_citations["citation_years"] = temporal_citations["COLLECT(c.date)"].apply(
        lambda x: [int(i[:4]) for i in eval(x)]
    )
    temporal_citations["post_publication_year_citations"] = temporal_citations[
        ["pub_year", "citation_years"]
    ].apply(lambda x: Counter([i - x.pub_year for i in x.citation_years]), axis=1)
    temporal_citations["pub_fields_list"] = temporal_citations["pub_fields"].apply(
        lambda x: [i[0] for i in eval(x)]
    )
    temporal_citations = temporal_citations[
        ["pub_year", "pub_fields_list", "post_publication_year_citations"]
    ].explode("pub_fields_list")

    citations_t = pd.DataFrame.from_records(
        list(temporal_citations["post_publication_year_citations"].values),
        columns=np.arange(0, 2023 - temporal_citations["pub_year"].min(), 1),
    ).fillna(0)

    citations_t["field"] = temporal_citations["pub_fields_list"].values

    grouped = citations_t.groupby("field").mean()
    grouped_counts = citations_t.groupby("field").count()

    # plot cumulative average citation rates per year after publication
    plt.clf()
    sns.set_style("whitegrid")
    sns.set(font_scale=1.5)
    plt.figure(figsize=(10, 16))
    lineplot = sns.lineplot(
        grouped.T.cumsum(),
        palette=sns.color_palette("Set2"),
        dashes=False,
        legend=False,
    )
    for line, name in zip(lineplot.lines, grouped.T.columns):
        x, y = line.get_data()
        e = np.random.uniform(-0.25, 0.25, 1)[0]
        lineplot.text(
            x[-1],
            y[-1] + e,
            "  " + name + ": " + str(grouped_counts.loc[name][0]),
            verticalalignment="center",
            horizontalalignment="left",
            color=line.get_color(),
            fontsize=20,
        )

    plt.xlabel("Years After Publication")
    plt.ylabel("Average Citation")
    plt.title("Mean Citations per Field per Year Post Publication")
    plt.tight_layout()
    ax = plt.gca()

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    # plot average citation rates per year after publication
    plt.clf()
    sns.set_style("whitegrid")
    sns.set(font_scale=1)
    fig, ax = plt.subplots()
    sns.lineplot(
        citations_t[citations_t.columns[:-1]].mean(axis=0),
        palette=sns.color_palette("Set2"),
        dashes=False,
        legend=False,
    )
    plt.xlabel("Years After Publication")
    plt.ylabel("Average Citation")
    plt.title("Mean Citations Per Year Post Publication")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()
    return

def summary_diversity(rep):
    """"Overall diversity heatmaps and correlation between weighted and unweighted.
    
    Args:
        rep(html_report): report.
    """

    # scatter plots of researcher diversity by number of publications
    rep.add_markdown(
        f"We think about diversity of grantees as a measure of how diverse their publication \
                     track record is. For example, is a researcher published exclusively in Biological Sciences \
                     This is very diverse. Whereas researchers who, say, publish across an even spread of fields \
                     are more diverse. Diversity is measured as the probability than any to field tags from a \
                     researchers publication history are different. In the case of Rao-Stirling (RS), pairwise \
                     probabilities are weighted by the similarity matrix of fields. Below shows the similarity \
                     heatmaps of both Cosine and Citation similarity."
    )
    sns.set(font_scale=1.2)
    fig = plt.figure(figsize=(10, 10))
    sns.heatmap(idr.cosine_similarity, square=True)
    plt.title("Cosine Similarity")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    fig = plt.figure(figsize=(10, 10))
    sns.heatmap(idr.citation_similarity, square=True)
    plt.title("Citation Similarity")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()
    sns.set(font_scale=1)

    # distribution and correlation of diversity metrics
    rep.add_markdown(f"Team Diversity Cosine and Citation")
    palette = sns.color_palette("Set2")
    color_dict = {}
    for i, groups in enumerate(teams["top_supergroups"].value_counts().index):
        if i <= 5:
            color_dict[groups] = palette[i]
        else:
            color_dict[groups] = "white"

    plt.clf()
    sns.set_style("ticks")
    fig, ax = plt.subplots(2, 2)
    g = sns.jointplot(
        teams,
        x="simpson_diversity",
        y="rs_cosine",
        hue="top_supergroups",
        ax=ax,
        legend=False,
        s=20,
        alpha=0.5,
        linewidth=0,
        palette=color_dict,
    )

    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    plt.xlim((0, 1))
    plt.ylim((0, 0.7))
    # Add mean lines
    plt.axhline(teams["rs_cosine"].mean(), color="gray", linestyle="--")
    plt.axvline(teams["simpson_diversity"].mean(), color="gray", linestyle="--")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    plt.clf()
    fig, ax = plt.subplots()
    g = sns.jointplot(
        teams,
        x="simpson_diversity",
        y="rs_citation",
        hue="top_supergroups",
        ax=ax,
        legend=False,
        s=20,
        alpha=0.5,
        linewidth=0,
        palette=color_dict,
    )

    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    plt.xlim((0, 1))
    plt.ylim((0, 0.7))
    plt.axhline(teams["rs_citation"].mean(), color="gray", linestyle="--")
    plt.axvline(teams["simpson_diversity"].mean(), color="gray", linestyle="--")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    g = sns.jointplot(
        teams,
        x="rs_cosine",
        y="rs_citation",
        hue="top_supergroups",
        ax=ax,
        s=20,
        alpha=0.5,
        linewidth=0,
        palette=color_dict,
    )
    top = teams["top_supergroups"].value_counts().index[:6]
    handles, labels = g.ax_joint.get_legend_handles_labels()
    idx = [labels.index(group) for group in top]
    handles = [handles[i] for i in idx]
    labels = [labels[i] for i in idx]
    fig, ax = plt.subplots()
    ax.legend(handles, labels, loc="center")
    ax.axis("off")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    rep.add_markdown(f"Output Diversity Cosine and Citation")

    # distribution and correlation of diversity metrics
    palette = sns.color_palette("Set2")
    color_dict = {}
    for i, groups in enumerate(outputs["pub_fields"].astype(str).value_counts().index):
        if i <= 5:
            color_dict[groups] = palette[i]
        else:
            color_dict[groups] = "white"

    outputs["pub_fields"] = outputs["pub_fields"].astype(str)
    plt.clf()
    sns.set_style("ticks")
    fig, ax = plt.subplots(2, 2)
    g = sns.jointplot(
        outputs,
        x="simpson_diversity",
        y="rs_cosine",
        hue="pub_fields",
        ax=ax,
        legend=False,
        s=20,
        alpha=0.5,
        linewidth=0,
        palette=color_dict,
    )
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    plt.xlim((0, 1))
    plt.ylim((0, 0.7))
    # Add mean lines
    plt.axhline(outputs["rs_cosine"].mean(), color="gray", linestyle="--")
    plt.axvline(outputs["simpson_diversity"].mean(), color="gray", linestyle="--")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    plt.clf()
    fig, ax = plt.subplots()
    g = sns.jointplot(
        outputs,
        x="simpson_diversity",
        y="drs_citation",
        hue="pub_fields",
        ax=ax,
        legend=False,
        s=20,
        alpha=0.5,
        linewidth=0,
        palette=color_dict,
    )
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    plt.xlim((0, 1))
    plt.ylim((0, 0.7))
    plt.axhline(outputs["drs_citation"].mean(), color="gray", linestyle="--")
    plt.axvline(outputs["simpson_diversity"].mean(), color="gray", linestyle="--")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    g = sns.jointplot(
        outputs,
        x="rs_cosine",
        y="drs_citation",
        hue="pub_fields",
        ax=ax,
        s=20,
        alpha=0.5,
        linewidth=0,
        palette=color_dict,
    )
    top = outputs["pub_fields"].value_counts().index[:6]
    handles, labels = g.ax_joint.get_legend_handles_labels()
    idx = [labels.index(group) for group in top]
    handles = [handles[i] for i in idx]
    labels = [labels[i] for i in idx]
    fig, ax = plt.subplots()
    ax.legend(handles, labels, loc="center")
    ax.axis("off")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    rep.add_markdown(f"Impact Diversity Cosine and Citation")
    palette = sns.color_palette("Set2")
    color_dict = {}
    for i, groups in enumerate(impact["pub_fields"].astype(str).value_counts().index):
        if i <= 5:
            color_dict[groups] = palette[i]
        else:
            color_dict[groups] = "white"

    impact["pub_fields_str"] = impact["pub_fields"].astype(str)
    plt.clf()
    sns.set_style("ticks")
    fig, ax = plt.subplots(2, 2)
    g = sns.jointplot(
        impact,
        x="simpson_diversity",
        y="rs_cosine",
        hue="pub_fields_str",
        ax=ax,
        legend=False,
        s=20,
        alpha=0.5,
        linewidth=0,
        palette=color_dict,
    )

    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    plt.xlim((0, 1))
    plt.ylim((0, 0.7))
    # Add mean lines
    plt.axhline(impact["rs_cosine"].mean(), color="gray", linestyle="--")
    plt.axvline(impact["simpson_diversity"].mean(), color="gray", linestyle="--")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    plt.clf()
    fig, ax = plt.subplots()
    g = sns.jointplot(
        impact,
        x="simpson_diversity",
        y="rs_citation",
        hue="pub_fields_str",
        ax=ax,
        legend=False,
        s=20,
        alpha=0.5,
        linewidth=0,
        palette=color_dict,
    )

    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.0)
    plt.xlim((0, 1))
    plt.ylim((0, 0.7))
    plt.axhline(impact["rs_citation"].mean(), color="gray", linestyle="--")
    plt.axvline(impact["simpson_diversity"].mean(), color="gray", linestyle="--")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    g = sns.jointplot(
        impact,
        x="rs_cosine",
        y="rs_citation",
        hue="pub_fields_str",
        ax=ax,
        s=20,
        alpha=0.5,
        linewidth=0,
        palette=color_dict,
    )
    top = impact["pub_fields_str"].value_counts().index[:6]
    handles, labels = g.ax_joint.get_legend_handles_labels()
    idx = [labels.index(group) for group in top]
    handles = [handles[i] for i in idx]
    labels = [labels[i] for i in idx]
    fig, ax = plt.subplots()
    ax.legend(handles, labels, loc="center")
    ax.axis("off")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()
    return

def summary_diversity_teams(rep):
    """"Analysis of team diversity.
    
    Args:
        rep(html_report): report.
    """

    # scatter plots of researcher diversity by number of publications
    ax = sns.scatterplot(
        teams,
        y="rs_cosine",
        x="no_pubs",
        hue="top_supergroups",
        s=10,
        edgecolor=None,
        legend=False,
    )
    sns.regplot(data=teams, y="rs_cosine", x="no_pubs", scatter=False, ax=ax)
    plt.axhline(teams["rs_cosine"].mean(), color="black", linestyle="--")
    plt.axvline(teams["no_pubs"].mean(), color="black", linestyle="--")
    plt.title(
        "Scatter Plot of Researcher RS-Cosine Diversity by Number of Publications"
    )
    plt.xlabel("Number of Publications prior to Grant Start Date")
    plt.ylabel("Diversity")
    plt.xlim(0, 200)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    ax = sns.scatterplot(
        teams[teams["no_pubs"] >= 20],
        y="rs_cosine",
        x="no_pubs",
        hue="top_supergroups",
        s=10,
        edgecolor=None,
        legend=False,
    )
    sns.regplot(
        data=teams[teams["no_pubs"] >= 20],
        y="rs_cosine",
        x="no_pubs",
        scatter=False,
        ax=ax,
    )
    plt.axhline(
        teams[teams["no_pubs"] >= 20]["rs_cosine"].mean(), color="black", linestyle="--"
    )
    plt.axvline(
        teams[teams["no_pubs"] >= 20]["no_pubs"].mean(), color="black", linestyle="--"
    )
    plt.title(
        "Scatter Plot of Researcher RS-Cosine Diversity by Number of Publications"
    )
    plt.xlabel("Number of Publications prior to Grant Start Date")
    plt.ylabel("Diversity")
    plt.xlim(0, 200)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    rep.add_markdown(
        f"The average number of publications per researcher is now {teams[teams['no_pubs'] >= 20]['no_pubs'].mean()} and the average cosine diversity per researcher is now {teams[teams['no_pubs'] >= 20]['rs_cosine'].mean()}"
    )

    # plot of researcher diversity by field
    sub_teams = teams[teams["no_pubs"] >= 20]
    mean = sub_teams["rs_cosine"].mean()
    sub_teams["researcher_field"] = sub_teams.apply(
        lambda x: str(set(eval(x.top_supergroups)))
        if x.rs_cosine >= mean
        else str(eval(x.top_supergroups)[0]),
        axis=1,
    )
    grouped = (
        sub_teams[["researcher_field", "rs_cosine"]]
        .groupby("researcher_field")
        .median()
    )
    counts = (
        sub_teams[["researcher_field", "rs_cosine"]].groupby("researcher_field").count()
    )
    grouped = grouped.loc[list(counts[counts["rs_cosine"] > 1].index)]
    grouped["field"] = [str(i) for i in grouped.index]

    order = grouped.sort_values(by="rs_cosine", ascending=False).index

    plt.clf()
    sns.set(font_scale=0.7)
    sns.set_style("whitegrid")
    sns.boxplot(
        sub_teams[["researcher_field", "rs_cosine"]],
        y="researcher_field",
        x="rs_cosine",
        hue="researcher_field",
        order=order,
    )
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()
    return

def summary_diversity_outputs(rep):
    """"Analysis of outputs diversity.
    
    Args:
        rep(html_report): report.
    """

    # scatter plots of output diversity by number of publications
    ax = sns.scatterplot(
        outputs,
        y="rs_cosine",
        x="no_refs",
        hue="pub_fields",
        s=10,
        edgecolor=None,
        legend=False,
    )
    sns.regplot(data=outputs, y="rs_cosine", x="no_refs", scatter=False, ax=ax)
    plt.axhline(outputs["rs_cosine"].mean(), color="black", linestyle="--")
    plt.axvline(outputs["no_refs"].mean(), color="black", linestyle="--")
    plt.title("Scatter Plot of Researcher RS-Cosine Diversity by Number of References")
    plt.xlabel("Number of References")
    plt.ylabel("Diversity")
    plt.xlim(0, 200)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    ax = sns.scatterplot(
        outputs[outputs["no_refs"] >= 8],
        y="rs_cosine",
        x="no_refs",
        hue="pub_fields",
        s=10,
        edgecolor=None,
        legend=False,
    )
    sns.regplot(
        data=outputs[outputs["no_refs"] >= 8],
        y="rs_cosine",
        x="no_refs",
        scatter=False,
        ax=ax,
    )
    plt.axhline(
        outputs[outputs["no_refs"] >= 8]["rs_cosine"].mean(),
        color="black",
        linestyle="--",
    )
    plt.axvline(
        outputs[outputs["no_refs"] >= 8]["no_refs"].mean(),
        color="black",
        linestyle="--",
    )
    plt.title(
        "Scatter Plot of Researcher RS-Cosine Diversity by Number of Publications"
    )
    plt.xlabel("Number of Publications prior to Grant Start Date")
    plt.ylabel("Diversity")
    plt.xlim(0, 200)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    rep.add_markdown(
        f"The total number of publications is now {outputs[outputs['no_refs'] >= 8].shape[0]} and the average cosine diversity per publication is now {outputs[outputs['no_refs'] >= 8]['rs_cosine'].mean()}"
    )

    # plot of output diversity by field
    sub_outputs = outputs[outputs["no_refs"] >= 8]
    sub_outputs["rs_cosine"].mean()
    sub_outputs["pub_field_unique"] = sub_outputs.apply(
        lambda x: list(set([i[0] for i in eval(x.pub_fields)])), axis=1
    )
    sub_outputs = sub_outputs[["pub_fields", "rs_cosine"]].explode("pub_fields")

    sub_outputs = sub_outputs.reset_index()
    grouped = sub_outputs[["pub_fields", "rs_cosine"]].groupby("pub_fields").median()
    counts = sub_outputs[["pub_fields", "rs_cosine"]].groupby("pub_fields").count()
    grouped = grouped.loc[list(counts[counts["rs_cosine"] > 1].index)]
    grouped["field"] = [str(i) for i in grouped.index]

    order = grouped.sort_values(by="rs_cosine", ascending=False).index

    plt.clf()
    sns.set(font_scale=0.7)
    sns.set_style("whitegrid")
    sns.boxplot(
        sub_outputs,
        y="pub_fields",
        x="rs_cosine",
        hue="pub_fields",
        order=order,
        legend=False,
    )
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()
    return

def summary_diversity_impact(rep):
    """"Analysis of impact diversity.
    
    Args:
        rep(html_report): report.
    """

    # scatter plots of citation diversity by number of citations.
    ax = sns.scatterplot(
        impact,
        y="rs_cosine",
        x="no_cite",
        hue="pub_fields_str",
        s=10,
        edgecolor=None,
        legend=False,
    )
    sns.regplot(data=impact, y="rs_cosine", x="no_cite", scatter=False, ax=ax)
    plt.axhline(impact["rs_cosine"].mean(), color="black", linestyle="--")
    plt.axvline(impact["no_cite"].mean(), color="black", linestyle="--")
    plt.title("Scatter Plot of Citation RS-Cosine Diversity by Number of Citations")
    plt.xlabel("Number of Citations")
    plt.ylabel("Diversity")
    plt.xlim(0, 200)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    ax = sns.scatterplot(
        impact[impact["no_cite"] >= 10],
        y="rs_cosine",
        x="no_cite",
        hue="pub_fields_str",
        s=10,
        edgecolor=None,
        legend=False,
    )
    sns.regplot(
        data=impact[impact["no_cite"] >= 19],
        y="rs_cosine",
        x="no_cite",
        scatter=False,
        ax=ax,
    )
    plt.axhline(
        impact[impact["no_cite"] >= 10]["rs_cosine"].mean(),
        color="black",
        linestyle="--",
    )
    plt.axvline(
        impact[impact["no_cite"] >= 10]["no_cite"].mean(), color="black", linestyle="--"
    )
    plt.title("Scatter Plot of Citation RS-Cosine Diversity by Number of Citations")
    plt.xlabel("Number of Citations")
    plt.ylabel("Diversity")
    plt.xlim(0, 200)
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    rep.add_markdown(
        f"The average diffusion cosine diversity per publication is now {impact[impact['no_cite'] >= 10]['rs_cosine'].mean()}"
    )

    # plot of output diversity by field
    sub_outputs = impact[impact["no_cite"] >= 10]
    sub_outputs = sub_outputs[["pub_fields", "rs_cosine"]].explode("pub_fields")

    sub_outputs = sub_outputs.reset_index()
    grouped = sub_outputs[["pub_fields", "rs_cosine"]].groupby("pub_fields").median()
    counts = sub_outputs[["pub_fields", "rs_cosine"]].groupby("pub_fields").count()
    grouped = grouped.loc[list(counts[counts["rs_cosine"] > 1].index)]
    grouped["field"] = [str(i) for i in grouped.index]

    order = grouped.sort_values(by="rs_cosine", ascending=False).index

    plt.clf()
    sns.set(font_scale=0.7)
    sns.set_style("whitegrid")
    sns.boxplot(
        sub_outputs,
        y="pub_fields",
        x="rs_cosine",
        hue="pub_fields",
        order=order,
        legend=False,
    )
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()
    return

def summary_report_grant_level(S3_OUTPUT_FOLDER, scheme_mapping):
    """Create html report analysis on basic descriptives from grants.
    
    Args:
        S3_OUTPUT_FOLDER(str): Output folder location which will also be used as save_path.
        scheme_mapping(str): Location of metadata for grants by scheme.
    """

    merged = read_from_s3(S3_OUTPUT_FOLDER + "/all_bygrant.csv")
    scheme = pd.read_csv(scheme_mapping)
    merged = merged.merge(scheme, left_on="g.original_source_id", right_on="Reference")
    rep = Report()
    rep.add_title("Analysis of Diversity Score Correlation")

    sns.set_style("white")
    sns.jointplot(
        merged,
        x="team_diversity",
        y="output_diversity",
        hue="Open mode / Directed",
        linewidth=0,
        alpha=0.5,
    )
    plt.axhline(merged["output_diversity"].mean(), color="gray", linestyle="--")
    plt.axvline(merged["team_diversity"].mean(), color="gray", linestyle="--")
    plt.ylabel("Output Diversity")
    plt.xlabel("Team Diversity")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    sns.jointplot(
        merged,
        x="output_diversity",
        y="impact_diversity",
        hue="Open mode / Directed",
        linewidth=0,
        alpha=0.5,
    )
    plt.axhline(merged["impact_diversity"].mean(), color="gray", linestyle="--")
    plt.axvline(merged["output_diversity"].mean(), color="gray", linestyle="--")
    plt.ylabel("Impact Diversity")
    plt.xlabel("Output Diversity")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    sns.jointplot(
        merged,
        x="team_diversity",
        y="impact_diversity",
        hue="Open mode / Directed",
        linewidth=0,
        alpha=0.5,
    )
    plt.axhline(merged["impact_diversity"].mean(), color="gray", linestyle="--")
    plt.axvline(merged["team_diversity"].mean(), color="gray", linestyle="--")
    plt.ylabel("Impact Diversity")
    plt.xlabel("Team Diversity")
    plt.tight_layout()
    plt.draw()
    rep.add_figure()
    plt.clf()

    rep.write_report(filename = "./vis/reports/summary_diversity_correlation.html")
    return
