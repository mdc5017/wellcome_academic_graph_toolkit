from .utils import (
    calculate_diversity,
    get_ids,
    cosine_matrix,
    citation_matrix
)
from .vis_utils import summary_reports, summary_report_grant_level
from .process import aggregate_grant_level
from .vis import idr_types, topic_treemap, topic_diversity, subfield_treemap, subfield_diversity
import time
import argparse 

parser = argparse.ArgumentParser(description='Calculate diversity of Potfolio')
parser.add_argument('S3_OUTPUT_FOLDER', metavar='output_path', type=str,
                    default="funding_impact_measures/idr/dr_test",
                    help='folder to save analysis outputs.', nargs="?")
parser.add_argument('parallel', metavar='parallel_cpus', type=bool,
                    default=True, nargs="?",
                    help='whether to utilise multiple cpu cores.')
parser.add_argument('scheme_mapping', metavar='scheme_type_path', type=str,
                    default="./idr/input/DRscheme_mapping.csv",
                    help='location of scheme types metadata',  nargs="?")
parser.add_argument('award_mapping', metavar='award_mapping_path', type=str,
                    default="./idr/input/Awards.csv",
                    help='location of grant award metadata', nargs="?")
parser.add_argument('input_path', metavar='input_path', type=str, nargs="?",
                    default="funding_impact_measures/dr_grants/dr_pub_grant_links.xlsx",
                    help='location of publication and grant dimension ids')
args = parser.parse_args()

if __name__ == "__main__":
    start_time = time.time()
    # read grant and pub ids
    grant_ids, pub_ids = get_ids(
        fname=args.input_path
    )
    # calculate knowledge_integration/reference list to allow for cosine similarity calculation
    df = calculate_diversity(
        pub_ids,
        dim="knowledge_integration",
        S3_OUTPUT_FOLDER=args.S3_OUTPUT_FOLDER,
        parallel=args.parallel,
        weighted=None,
    )
    cosine_matrix(df, args.S3_OUTPUT_FOLDER)
    citation_matrix(df, args.S3_OUTPUT_FOLDER)

    # calculate diversity using similarity weights for portfolio
    dimensions = ["grantees_fields", "knowledge_integration", "knowledge_diffusion"]
    for dim in dimensions:
        calculate_diversity(
            pub_ids,
            grant_ids,
            dim=dim,
            S3_OUTPUT_FOLDER=args.S3_OUTPUT_FOLDER,
            parallel=args.parallel,
            weighted=True,
        )

    # output data summaries as html report
    summary_reports(args.S3_OUTPUT_FOLDER, basic=True, diversity=True)

    # aggregate and group to grant-level
    aggregate_grant_level(args.S3_OUTPUT_FOLDER)
    summary_report_grant_level(args.S3_OUTPUT_FOLDER, args.scheme_mapping)

    # output plotly visualisations as html
    print ('Computing final plotly visualisations')
    idr_types(args.S3_OUTPUT_FOLDER, args.scheme_mapping, args.award_mapping)
    topic_treemap(args.S3_OUTPUT_FOLDER, args.award_mapping)
    topic_diversity(args.S3_OUTPUT_FOLDER, args.award_mapping)
    subfield_diversity(args.S3_OUTPUT_FOLDER)
    subfield_treemap(args.S3_OUTPUT_FOLDER, args.award_mapping)

    print ('Pipeline Complete in %s minutes'% str((time.time() - start_time)/60))
