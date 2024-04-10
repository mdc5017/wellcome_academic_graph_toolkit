from html_reports.reports import Report
from career_viz_calcs import VizCalcs
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import pandas as pd

rep = Report()
Viz_calcs = VizCalcs()

def RCR_viz():
    """
    Plots the histogram of all RCR values
    """
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
    """
    Plots the histogram of all RCR log values
    """

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

    for funder in Viz_calcs.funders:
        funder_RCR_log_list = Viz_calcs.RCR_log_list[funder]
        hist_values_funder, _ = np.histogram(funder_RCR_log_list, bins=100, density=True)
        ax.plot(bin_centers, hist_values_funder, label=funder)

    # plot 95th percentile for all funders
    funders_RCR_log_list = [Viz_calcs.RCR_log_list[funder] for funder in Viz_calcs.funders]
    funders_RCR_log_list = [item for sublist in funders_RCR_log_list for item in sublist]
    percentile_95 = np.percentile(funders_RCR_log_list, 95)
    plt.axvline(percentile_95, color='red', linestyle='dashed', linewidth=2, label='95th Percentile')
    plt.xlabel('RCR log')
    plt.ylabel('Count')
    ax.legend(bbox_to_anchor=(1.05, 1),loc='upper left', borderaxespad=0.)
    plt.text(percentile_95, plt.ylim()[1], f'95th Percentile\n{percentile_95:.2f}', color='red', verticalalignment='bottom', horizontalalignment='right')
    plt.tight_layout()

    
def researchers_per_field_viz():
    """
    Creates a plot showing the proportion of researchers per field per funder
    """
    Viz_calcs.researchers_per_field()

    keys = list(Viz_calcs.researcher_field_count[Viz_calcs.funders[0]].keys())
    _, ax = plt.subplots(figsize=(12, 6))
    width = 0.15
    theta = np.arange(len(keys))

    for funder in Viz_calcs.funders:
        plot_data = Viz_calcs.researcher_field_count[funder]
        plot_data = [plot_data[key] for key in keys]
        r = [value / sum(plot_data) for value in plot_data]
        # vary the width for each funder so the bars are plotted next to eachother
        ax.bar(theta + width * Viz_calcs.funders.index(funder), r, width, label=funder)
        ax.set_xticks(theta)
        ax.set_xticklabels(keys, rotation=45, ha='right') 
        ax.set_title('What proportion of researchers are associated with different Fields of Research?')
        ax.legend()
    plt.tight_layout()
    plt.show()

def researchers_per_field_viz_above_thresh():
    """
    Creates a plot showing the proportion of researchers per field per funder over the 95th percentile
    """
    Viz_calcs.researchers_per_field_above_threshold()
    Viz_calcs.researchers_per_field() #of which we have RCR

    keys = Viz_calcs.fields
    _, ax = plt.subplots(figsize=(12, 6))
    width = 0.15
    theta = np.arange(len(keys))

    for funder in Viz_calcs.funders:
        plot_data_numerator = Viz_calcs.researcher_field_count_above_thresh[funder]
        plot_data_denominator = Viz_calcs.researcher_field_count[funder]
        plot_data_numerator = [plot_data_numerator[key] for key in keys]
        plot_data_denominator = [plot_data_denominator[key] for key in keys]

        r = [value / sum(plot_data_denominator) for value in plot_data_numerator]
        # vary the width for each funder so the bars are plotted next to eachother
        ax.bar(theta + width * Viz_calcs.funders.index(funder), r, width, label=funder)
        ax.set_xticks(theta)
        ax.set_xticklabels(keys, rotation=45, ha='right') 
        ax.set_title('What proportion of researchers have RCR log above threshold for different Fields of Research?')
        ax.legend()
    plt.tight_layout()
    plt.show()
    
def pubs_per_field_viz_above_thresh():
    """
    Creates a plot showing the proportion of publications per field per funder over the 95th percentile
    """

    Viz_calcs.publications_per_field()

    keys = Viz_calcs.fields
    _, ax = plt.subplots(figsize=(12, 6))
    width = 0.15
    theta = np.arange(len(keys))

    for funder in Viz_calcs.funders:
        plot_data_numerator = [Viz_calcs.pubs_field_count_above_thresh[funder][key] for key in keys]
        plot_data_denominator = [Viz_calcs.pubs_field_count[funder][key] for key in keys]

        r = [value / sum(plot_data_denominator) for value in plot_data_numerator]
        # vary the width for each funder so the bars are plotted next to eachother
        ax.bar(theta + width * Viz_calcs.funders.index(funder), r, width, label=funder)
        ax.set_xticks(theta)
        ax.set_xticklabels(keys, rotation=45, ha='right') 
        ax.set_title('What proportion of publications have a RCR log above the threshold for different Fields of Research?')
        ax.legend()
    plt.tight_layout()
    plt.show()


def RCR_log_across_DR_schemes():
    """
    Calculates the proportion of RCR log above threshold for different DR funding schemes
    """
    Viz_calcs.RCR_log_per_DR_scheme()

    keys = Viz_calcs.DR_scheme_labels
    r = [Viz_calcs.DR_scheme_RCR_log_above_thresh_len[key]/Viz_calcs.DR_scheme_RCR_log_len[key] for key in keys]
    _, ax = plt.subplots(figsize=(12, 5))

    ax.bar(keys, r)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(keys, rotation=45)

    plt.title('Does the proportion of RCR log above threshold change for different DR funding schemes?')
    plt.tight_layout()
    plt.show()

def RCR_around_funding():
    """
    Calculates the proportion of RCR log above the threshold before and after funding
    """
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

    ax.set_title('Does the proportion of RCR log above threshold change after funding?')
    plt.legend()
    plt.tight_layout()
    plt.show()

def years_from_first_to_last_author_position_viz():
    """
    Creates a plot showing the years from first to last author position
    """
    hist_values, hist_bins = Viz_calcs.years_from_first_to_last_author_position()

    _, ax = plt.subplots(figsize=(16, 8))
    for funder in Viz_calcs.funders:
        ax.plot((hist_bins[funder][:-1] + hist_bins[funder][1:])/2, hist_values[funder], label=funder)

    plt.xlim(0, 20)
    plt.xlabel('Years between first and last author position')
    plt.ylabel('Distribution')
    plt.title('How long did it take researchers to go from first to last author position?')
    plt.legend()


def RCR_log_over_time_viz():
    """
    Creates a plot showing the RCR log over time for the different funders
    """
    Viz_calcs.RCR_log_over_time()
    _, ax = plt.subplots(figsize=(10, 6))

    for funder in Viz_calcs.funders[0:4]:
        ax.plot(Viz_calcs.RCR_log_over_time.index, Viz_calcs.RCR_log_over_time[f'funder_{funder}_RCR_log_proportion'], marker='o', linestyle='-', label=funder)

    plt.xlabel('Year')
    plt.ylabel('Proportion')
    plt.title('Proportion of publications over the 95th percentile RCR log threshold by funder')
    plt.legend()
    plt.show()



def years_since_first_pub_viz():
    """
    Creates a plot showing the years from first to last author position
    """
    hist_values, hist_bins = Viz_calcs.years_since_first_pub()

    _, ax = plt.subplots(figsize=(16, 8))
    for funder in Viz_calcs.funders:
        ax.plot((hist_bins[funder][:-1] + hist_bins[funder][1:])/2, hist_values[funder], label=funder)

    plt.xlim(1, 20)
    plt.ylim(0, 0.2)
    plt.xlabel('Years between since first author position')
    plt.ylabel('Distribution')
    plt.title('How long have researchers been publishing?')
    plt.legend()

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
        years, and spread across {Viz_calcs.num_fields} fields"
    )
    RCR_viz()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown(f"The RCR values for the different fields are closely sqeezed to zero \
                     and there are a lot of outliers that aren't on the plot where RCR exceeds 100, \
                     for some publications even exceeding 1000."
    )

    rep.add_markdown(
        f"Our aim is to find a proportion of papers that we can relate back to Wellcome grants \
                     that have had a significant influence. To talk about significance, the distribution of RCR values \
                     can be made to resemble a normal distribution by taking the natural logarithm of each RCR value. \
                     In fact, it passes the Shapiro-Wilk test for normality, the test statistic is {np.percentile(stats.shapiro(Viz_calcs.RCR_list).statistic, 95):.5f}.\
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
            particularly influential. The 95th percentile is set at {np.percentile(Viz_calcs.RCR_list, 95):.2f}."
    )

    RCR_hist()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown(f"This seemed like a great cut-off to analyse our 'influential' researchers and publications but when considering \
                     related funder publications, it becomes clear that this cut-off is too low: all funders under consideration \
                     are performing particularly well compared to the general distribution of RCR log scores of all papers over the last 20 years. \
                     As such, it makes sense to consider a higher cut-off. *We propose to call a paper significant if it exceeds 95 percent of RCR log \
                     scores of all funders publications*. This cut-off is set at {Viz_calcs.career.RCR_log_threshold}. The below graph might look like this is a bit low, \
                     given the distribution of DR, MRC and NIHR in particular, but the number of publications relate to Wellcome is far higher, see the following section."
    )
    RCR_hist_funders()
    rep.add_figure(options="width = 70%") 

    rep.add_title("Funder comparison based on RCR log threshold", level=2)
    rep.add_markdown(
        "This analysis considers researchers over the last 20 years that are authors on publications that can be related back to any of the following funders: ")
    rep.add_markdown(f"   * Discovery Research ('DR'), with {'{:,}'.format(len(Viz_calcs.RCR_log_list['DR']))} papers linked back with an RCR score, of which {'{:.1%}'.format(len(Viz_calcs.RCR_log_list_above_threshold['DR'])/len(Viz_calcs.RCR_log_list['DR']))} is above the RCR log threshold")
    rep.add_markdown(f"   * the Wellcome Trust ('Wellcome'), with {'{:,}'.format(len(Viz_calcs.RCR_log_list['wellcome']))} papers linked back with an RCR score, of which {'{:.1%}'.format(len(Viz_calcs.RCR_log_list_above_threshold['wellcome'])/len(Viz_calcs.RCR_log_list['wellcome']))} is above the RCR log threshold")
    rep.add_markdown(f"   * the Medical Research Council ('MRC'), with {'{:,}'.format(len(Viz_calcs.RCR_log_list['MRC']))} papers linked back with an RCR score, of which {'{:.1%}'.format(len(Viz_calcs.RCR_log_list_above_threshold['MRC'])/len(Viz_calcs.RCR_log_list['MRC']))} is above the RCR log threshold")
    rep.add_markdown(f"   * the National Institute for Health Research ('NIHR'), with {'{:,}'.format(len(Viz_calcs.RCR_log_list['NIHR']))} papers linked back with an RCR score, of which {'{:.1%}'.format(len(Viz_calcs.RCR_log_list_above_threshold['NIHR'])/len(Viz_calcs.RCR_log_list['NIHR']))} is above the RCR log threshold")

    rep.add_markdown("Before considering the RCR log threshold as a metric, let's have a look what research fields the researchers associated to the papers that tie back to the funders of interest, research in. \
                     Research fields are determined by Field Of Research, a category assigned by Dimensions. \
                     Unsurprisingly the biomedical and clinical sciences, health sciences and biological sciences are very prevalent.")

    researchers_per_field_viz()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown("The following graph shows by field what proportion of researchers we would consider influential. \
                     In this case, we define 'influential' if the researcher was an author of at least one publication \
                     that exceeded the RCR log threshold. \
                     The proportions are very similar when it comes to the main fields all funders are working in such as \
                     health sciences, biomedical and clinical sciences and biological sciences (although NIHR shows a slight increase in the latter).\
                     A downside of this methodology is that it is very generous: as soon as a researcher is an author on a paper that exceeds the threshold, they are considered influential."
    )
    researchers_per_field_viz_above_thresh()
    rep.add_figure(options="width = 70%") 

    # rep.add_markdown("Instead of looking at researchers and deciding from what point a researcher is influential, \
    #                  it is much easier to consider the proportion of publications that exceed the RCR log threshold. \
    #                  This is what the graph below shows."
    # )
    # pubs_per_field_viz_above_thresh()
    # rep.add_figure(options="width = 70%") 

    rep.add_markdown("Let's now have a look at how the different DR schemes compare in terms of the proportion of RCR log above threshold. \
                     It looks like the directed portfolio has a slightly increased proportion of publications with a RCR log above threshold."
    )

    RCR_log_across_DR_schemes()
    rep.add_figure(options="width = 70%") 
    # rep.write_report()

    rep.add_markdown("We can also look through the lens of when we started funding a researcher and if the proportion of 'influential' papers (i.e. papers with an RCR log score \
                     exceeding the threshold) \
                     increased or decreased since our funding. The below shows this for the DR grants"
    )
    RCR_around_funding()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown("The following graph shows how the proportion of 'influential' papers have changed over time for each functions.")
    RCR_log_over_time_viz()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown("To get a sense of improvement in seniority of our researchers, we can have a look at how long it took those researchers to go from first to last author position. \
                     The idea being that early in a career, researchers are more likely to be first author, and later in their career, they are more likely to be last author. \
                     How do the different funders compare in this respect? The graph below shows all funders fund in a similar way, i.e. there seems more funding towards \
                     researchers that have progressed quickly from first to last author position rather than slowly.") 
                     
    years_from_first_to_last_author_position_viz()
    rep.add_figure(options="width = 70%") 

    rep.add_markdown("Finally, we can look at how long researchers have been publishing. We can do this by looking at their first publication and compare it to their last. \
                     A caveat with this methodology is that it doesn't take into account any career gaps. By proxy, it does provide an indicator of how long a researcher has been active in the field. \
                     The graph below shows that in fact Discovery Research funds more people earlier on in their career than the other funders who seem to prefer later career researchers.")
                     
    years_since_first_pub_viz()
    rep.add_figure(options="width = 70%") 

    rep.write_report()