from html_reports.reports import Report
from career_viz_calcs import VizCalcs
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import pandas as pd

rep = Report()
Viz_calcs = VizCalcs()

def RCR_viz():
    fig, ax = plt.subplots(figsize=(16, 8))
    # Plot histograms for each label as a line graph
    for label, values in Viz_calcs.RCR_distribution_data.items():
        # normalise
        hist_values, bin_edges = np.histogram(values, bins=4000, density=True)
        hist_values = hist_values / sum(hist_values)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        ax.plot(bin_centers, hist_values, label=label)

    # Set labels and title
    ax.set_xlabel('RCR values')
    ax.set_xlim(0,4)
    ax.set_ylabel('Count')
    # ax.set_ylim(0,10)
    ax.set_title('RCR histogram')
    # Add a legend
    ax.legend(bbox_to_anchor=(1.05, 1),loc='upper left', borderaxespad=0.)

    # Show the plot

    plt.tight_layout()
    plt.show()  

def RCR_log_viz():
    fig, ax = plt.subplots(figsize=(16, 8))
    # Plot histograms for each label as a line graph
    for label, values in Viz_calcs.RCR_log_distribution_data.items():
        # normalise
        hist_values, bin_edges = np.histogram(values, bins=30, density=True)
        hist_values = hist_values / sum(hist_values)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        ax.plot(bin_centers, hist_values, label=label)

    # Set labels and title
    ax.set_xlabel('RCR log values')
    ax.set_ylabel('Count')
    ax.set_title('RCR log histogram')
    # Add a legend
    ax.legend(bbox_to_anchor=(1.05, 1),loc='upper left', borderaxespad=0.)

    # Show the plot

    plt.tight_layout()
    plt.show()

def RCR_hist():
    """
    A histogram where we show the cut off for the 95th percentile
    """
    fig, ax = plt.subplots(figsize=(16, 8))
    x = Viz_calcs.RCR_list
    percentile_95 = np.percentile(x, 95)
    hist_values, bin_edges = np.histogram(x, bins=100, density=True)
    
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    ax.plot(bin_centers, hist_values)
    plt.axvline(percentile_95, color='red', linestyle='dashed', linewidth=2, label='95th Percentile')
    plt.xlabel('RCR log')
    plt.ylabel('Count')
    ax.legend(bbox_to_anchor=(1.05, 1),loc='upper left', borderaxespad=0.)
    plt.text(percentile_95, plt.ylim()[1], f'95th Percentile\n{percentile_95:.2f}', color='red', verticalalignment='bottom', horizontalalignment='right')
    plt.tight_layout()


def RCR_hist_funders():
    """
    Comparison of all histograms for all funders and all pubs
    """
    Viz_calcs.RCR_log_funder_lists()

    fig, ax = plt.subplots(figsize=(16, 8))
    x = Viz_calcs.RCR_list
    hist_values, bin_edges = np.histogram(x, bins=100, density=True)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    ax.plot(bin_centers, hist_values, label='All publications')

    # hist_values_Crick, _ = np.histogram(Viz_calcs.Crick_RCR_log_list, bins=100, density=True)
    hist_values_DR, _ = np.histogram(Viz_calcs.DR_RCR_log_list, bins=100, density=True)
    hist_values_MRC, _ = np.histogram(Viz_calcs.MRC_RCR_log_list, bins=100, density=True)
    hist_values_NIHR, _ = np.histogram(Viz_calcs.NIHR_RCR_log_list, bins=100, density=True)
    hist_values_Wellcome, _ = np.histogram(Viz_calcs.Wellcome_RCR_log_list, bins=100, density=True)

    # ax.plot(bin_centers, hist_values_Crick)
    ax.plot(bin_centers, hist_values_DR, label='DR')
    ax.plot(bin_centers, hist_values_MRC, label='MRC')
    ax.plot(bin_centers, hist_values_NIHR, label='NIHR')
    ax.plot(bin_centers, hist_values_Wellcome, label='Wellcome')

    # plot 95th percentile for all funders
    funders_RCR_log_list = [Viz_calcs.DR_RCR_log_list, Viz_calcs.MRC_RCR_log_list, Viz_calcs.NIHR_RCR_log_list, Viz_calcs.Wellcome_RCR_log_list]
    funders_RCR_log_list = [item for sublist in funders_RCR_log_list for item in sublist]
    percentile_95 = np.percentile(funders_RCR_log_list, 95)
    plt.axvline(percentile_95, color='red', linestyle='dashed', linewidth=2, label='95th Percentile')
    plt.xlabel('RCR log')
    plt.ylabel('Count')
    ax.legend(bbox_to_anchor=(1.05, 1),loc='upper left', borderaxespad=0.)
    plt.text(percentile_95, plt.ylim()[1], f'95th Percentile\n{percentile_95:.2f}', color='red', verticalalignment='bottom', horizontalalignment='right')
    plt.tight_layout()


    
def Researchers_per_field_viz():
    Viz_calcs.researchers_per_field()

    keys = list(set(Viz_calcs.career.FOR_hierarchy.values()))
    # r1 = [Viz_calcs.Crick_field_count[key] for key in keys]
    r2 = [Viz_calcs.DR_field_count[key] for key in keys]
    r3 = [Viz_calcs.MRC_field_count[key] for key in keys]
    r4 = [Viz_calcs.NIHR_field_count[key] for key in keys]
    r5 = [Viz_calcs.Wellcome_field_count[key] for key in keys]

    df = pd.DataFrame({
        # 'r1': [i / sum(r1) for i in r1],
        'r2': [i / sum(r2) for i in r2],
        'r3': [i / sum(r3) for i in r3],
        'r4': [i / sum(r4) for i in r4],
        'r5': [i / sum(r5) for i in r5],
        'theta': keys
    })

    fig, ax = plt.subplots(figsize=(12, 6))

    width = 0.15
    theta = np.arange(len(keys))

    # ax.bar(theta - 2 * width, df['r1'], width, label='Crick')
    ax.bar(theta - width, df['r2'], width, label='DR')
    ax.bar(theta, df['r3'], width, label='MRC')
    ax.bar(theta + width, df['r4'], width, label='NIHR')
    ax.bar(theta + 2 * width, df['r5'], width, label='Wellcome')
    ax.set_xticks(theta)
    ax.set_xticklabels(df['theta'], rotation=45, ha='right') 

    ax.set_title('Proportion of researchers by field of publications and by funder')
    ax.legend()
    plt.tight_layout()
    plt.show()

def RCR_log_above_threshold_viz():
    Viz_calcs.RCR_log_above_threshold()
    Viz_calcs.researchers_per_field() #of which we have RCR

    keys = list(set(Viz_calcs.career.FOR_hierarchy.values()))
    # r1 = [Viz_calcs.Crick_RCR_log_field_count[key]/Viz_calcs.Crick_pubs_field_count[key] if Viz_calcs.Crick_field_count[key]>0 else 0 for key in keys]
    r2 = [Viz_calcs.DR_RCR_log_field_count[key]/Viz_calcs.DR_field_count[key] if Viz_calcs.DR_field_count[key]>0 else 0 for key in keys]
    r3 = [Viz_calcs.MRC_RCR_log_field_count[key]/Viz_calcs.MRC_field_count[key] if Viz_calcs.MRC_field_count[key]>0 else 0 for key in keys]
    r4 = [Viz_calcs.NIHR_RCR_log_field_count[key]/Viz_calcs.NIHR_field_count[key] if Viz_calcs.NIHR_field_count[key]>0 else 0 for key in keys]
    r5 = [Viz_calcs.Wellcome_RCR_log_field_count[key]/Viz_calcs.Wellcome_field_count[key] if Viz_calcs.Wellcome_field_count[key]>0 else 0 for key in keys]

    df = pd.DataFrame({
        # 'r1': r1,
        'r2': r2,
        'r3': r3,
        'r4': r4,
        'r5': r5,
        'theta': keys
    })

    _, ax = plt.subplots(figsize=(12, 6))

    width = 0.15
    theta = np.arange(len(keys))

    # ax.bar(theta - 2 * width, df['r1'], width, label='Crick')
    ax.bar(theta - width, df['r2'], width, label='DR')
    ax.bar(theta, df['r3'], width, label='MRC')
    ax.bar(theta + width, df['r4'], width, label='NIHR')
    ax.bar(theta + 2 * width, df['r5'], width, label='Wellcome')
    ax.set_xticks(theta)
    ax.set_xticklabels(df['theta'], rotation=45, ha='right') 

    ax.set_title('Proportion of researchers having a RCR log in the 95th percentile by funder')
    ax.legend()
    plt.tight_layout()
    plt.show()
    
def RCR_log_pubs_above_threshold_viz():
    """
    
    """
    Viz_calcs.RCR_log_pubs_above_threshold()
    Viz_calcs.publications_per_field()

    keys = list(set(Viz_calcs.career.FOR_hierarchy.values()))
    # r1 = [Viz_calcs.Crick_RCR_log_field_count[key]/Viz_calcs.Crick_pubs_field_count[key] if Viz_calcs.Crick_field_count[key]>0 else 0 for key in keys]
    r2 = [Viz_calcs.DR_RCR_log_pubs_field_count[key]/Viz_calcs.DR_pubs_field_count[key] if Viz_calcs.DR_field_count[key]>0 else 0 for key in keys]
    r3 = [Viz_calcs.MRC_RCR_log_pubs_field_count[key]/Viz_calcs.MRC_pubs_field_count[key] if Viz_calcs.MRC_field_count[key]>0 else 0 for key in keys]
    r4 = [Viz_calcs.NIHR_RCR_log_pubs_field_count[key]/Viz_calcs.NIHR_pubs_field_count[key] if Viz_calcs.NIHR_field_count[key]>0 else 0 for key in keys]
    r5 = [Viz_calcs.Wellcome_RCR_log_pubs_field_count[key]/Viz_calcs.Wellcome_pubs_field_count[key] if Viz_calcs.Wellcome_field_count[key]>0 else 0 for key in keys]

    df = pd.DataFrame({
        # 'r1': r1,
        'r2': r2,
        'r3': r3,
        'r4': r4,
        'r5': r5,
        'theta': keys
    })

    _, ax = plt.subplots(figsize=(12, 6))

    width = 0.15
    theta = np.arange(len(keys))

    # ax.bar(theta - 2 * width, df['r1'], width, label='Crick')
    ax.bar(theta - width, df['r2'], width, label='DR')
    ax.bar(theta, df['r3'], width, label='MRC')
    ax.bar(theta + width, df['r4'], width, label='NIHR')
    ax.bar(theta + 2 * width, df['r5'], width, label='Wellcome')
    ax.set_xticks(theta)
    ax.set_xticklabels(df['theta'], rotation=45, ha='right') 

    ax.set_title('Proportion of publications having a RCR log in the 95th percentile by funder')
    ax.legend()
    plt.tight_layout()
    plt.show()


def RCR_log_across_DR_schemes():
    Viz_calcs.RCR_log_per_DR_scheme()

    keys = Viz_calcs.DR_scheme_labels
    r = [Viz_calcs.DR_scheme_RCR_log_above_thresh_len[idx]/Viz_calcs.DR_scheme_RCR_log_len[idx] for idx in range(0, len(keys))]

    _, ax = plt.subplots(figsize=(12, 5))

    ax.bar(keys, r)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(keys, rotation=45)

    plt.title('Proportion of publications having a RCR log in the 95th percentile by DR scheme')
    plt.tight_layout()
    plt.show()

def RCR_around_funding():
    Viz_calcs.RCR_log_pubs_since_funding()

    funders = Viz_calcs.funders
    values_before = [Viz_calcs.RCR_log_pubs_before_over_threshold[funder]/Viz_calcs.RCR_log_pubs_before[funder] for funder in funders]
    values_after = [Viz_calcs.RCR_log_pubs_after_over_threshold[funder]/Viz_calcs.RCR_log_pubs_after[funder] for funder in funders]
    plot_data = pd.DataFrame({"before funding": values_before, "after funding": values_after}, index = funders)

    _, ax = plt.subplots(figsize=(12, 6))

    width = 0.15
    theta = np.arange(len(funders))

    ax.bar(theta, plot_data["before funding"], width, label="before funding")
    ax.bar(theta + width, plot_data["after funding"], width, label="after funding")
    # ax.bar(theta + 2 * width, plot_data['MRC'], width, label='MRC')
    ax.set_xticks(theta)
    ax.set_xticklabels(plot_data.index, rotation=45, ha='right') 

    ax.set_title('Proportion of publications having a RCR log in the 95th percentile by funder')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    """
    Script to generate an automated report for the Discovery Research analysis of Careers
    """
    rep.add_title("Career analysis for Discovery Research")

    rep.add_title("RCR as a metric of influence", level=2)
    rep.add_markdown(
        f"The Relative Citation Ratio (RCR) is a [metric developed \
        by the NIH]( https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5012559/) \
        which provides a bibliometric assesment of scientific productivity. \
        Each publication receives a value which represents the number of \
        citations that publication has received, normalised for the number \
        of citations of the research field of that publication. Some research \
        fields receive more citations than others, hence field normalising helps in \
        creating a metric that is more comparable across fields."
        )
    rep.add_markdown(
        f"RCR is an important metric when trying to quantify the influence a publication has. \
        The plot below looks at the RCR of {'{:,}'.format(Viz_calcs.num_pubs)} publications over the last 20 \
        years, and spread across {Viz_calcs.fields} fields"
    )
    RCR_viz()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown(f"the RCR values for the different fields are closely sqeezed to zero \
                     and there are a lot of outliers that aren't on the plot where RCR exceeds 100, \
                     for some publications even exceeding 1000."
    )

    rep.add_markdown(
        f"Our aim is to find a proportion of papers that we can relate back to Wellcome grants \
                     that have had a significant influence. To talk about significance, the distribution of RCR values \
                     can be made to resemble a normal distribution by taking the natural logarithm of each RCR value. \
                     In fact, it passes the Shapiro-Wilk test for normality, the test statistic is {stats.shapiro(Viz_calcs.RCR_list).statistic}.\
                     The graph below shows the natural logarithm of the RCR values per field."
    )
    RCR_log_viz()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown(
        f"The distributions for the different Fields of Research were plotted to see if there would be much variability across \
        fields. Even though RCR is field normalised, it is good to see that in effect, the distributions are alike and for our \
        our analysis we wouldn't need to discrimenate between fields.\
        "
    )

    rep.add_markdown(
        f"The figure below shows the distribution of all papers and the 95th percentile cut-off for papers we can assume to be \
            particularly influential. The 95th percentile is set at {np.percentile(Viz_calcs.RCR_list, 95)}."
    )

    RCR_hist()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown("This seemed like a great cut-off to analyse our 'influential' researchers and publications but when considering \
                     the DR (and other funder) publications, it becomes clear that this cut-off is too low: all funders under consideration \
                     are performing particularly well compared to the general distribution of RCR log scores of all papers over the last 20 years. \
                     As such, it makes sense to consider a higher cut-off. We propose to call a paper significant if it exceeds 95 percent of RCR log \
                     scores of all funders publications."
    )
    RCR_hist_funders()
    rep.add_figure(options="width = 70%") 

    rep.add_title("Researchers under analysis", level=2)
    rep.add_markdown("This analysis considers researchers over the last 20 years that are authors on publications that can be related back to any of the following funders: ")
    rep.add_markdown(f"   * the Wellcome Trust ('Wellcome'), with {'{:,}'.format(len(Viz_calcs.DR_RCR_log_list))} papers linked back with an RCR score")
    rep.add_markdown(f"   * the Wellcome Trust ('Wellcome'), with {'{:,}'.format(len(Viz_calcs.Wellcome_RCR_log_list))} papers linked back with an RCR score")
    rep.add_markdown(f"   * the Medical Research Council ('MRC'), with {'{:,}'.format(len(Viz_calcs.MRC_RCR_log_list))} papers linked back with an RCR score")
    rep.add_markdown(f"   * the National Institute for Health Research ('NIHR'), with {'{:,}'.format(len(Viz_calcs.NIHR_RCR_log_list))} papers linked back with an RCR score")

    rep.add_markdown("Before we use this cut-off for our further analysis. Let's compare how this distribution of RCR log scores compares to the RCR log scores from ")

    rep.add_markdown("The following graph shows the proportion of each researchers across the different Fields of Research. \
                     Unsurprisingly the biomedical and clinical sciences, health sciences and biological sciences are very prevalent.")
    Researchers_per_field_viz()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown("The following graph shows by field what proportion of researchers we would consider influential. \
                     In this case, we define 'influential' if the researcher was an author of at least one publication \
                     that exceeded the RCR log threshold. \
                     The proportions are overall still very high, perhaps allowing for just one paper is a little bit too generous."
    )
    RCR_log_above_threshold_viz()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown("Instead of looking at researchers and deciding from what point a researcher is influential, \
                     it is much easier to consider the proportion of publications that exceed the RCR log threshold. \
                     This is what the graph below shows."
    )
    RCR_log_pubs_above_threshold_viz()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown("Rather than for Field of Research, we can also do this for DR funding scheme. This is shown below."
    )

    RCR_log_across_DR_schemes()
    rep.add_figure(options="width = 70%") 
    rep.write_report()

    rep.add_markdown("We can also look through the lens of when we started funding a researcher and if the proportion of 'influential' papers \
                     increased or decreased since our funding. The below shows this for the DR grants"
    )
    RCR_around_funding()
    rep.add_figure(options="width = 70%") 
    rep.write_report()