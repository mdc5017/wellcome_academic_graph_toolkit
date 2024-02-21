# Career and Bibliometrics analysis

The code in this folder can generate a report.html which details a career and bibliometric analysis which was (first) run for the Discovery Research team in Q4 2023.

## setup
Make a virtual environment:
```python3 -m venv venv```
and activate this environment: `source venv/bin/activate`. Now install the requirements file:
```pip install -r requirements.txt```

## file overview

* `career_pipeline.py` is the main pipeline file which loads and transforms career and bibliography data from the [Wellcome Academic Graph](https://github.com/wellcometrust/wellcome_academic_graph.git). Transformed data is saved on s3 under `datalabs-data/dimensions/careers/`. Most analysis relies on `s3://datalabs-data/dimensions/careers/exploded_career_data/researchers_exploded.csv`, which is a table one row per researcher and columns (often with lists) containing fields such as:
        * dimensions_researcher_id
        * RCR
        * dimensions_publication_id
        * date
        * funder_DR (whether or not DR has been a funder once for this researcher)
        * funder_crick (whether or not Francis Crick has been a funder once for this researcher)
        * funder_NIHR (whether or not NIHR has been a funder once for this researcher)
        * funder_MRC (whether or not MRCC has been a funder once for this researcher)
        * funder_wellcome (whether or not Wellcome has been a funder once for this researcher)
        * author_position (first, middle or last for each publication)
        * pub_FOR (Fields OF Research for each publication)
        * grant_FOR
        * pub_FOR_super
        * grant_FOR_super
        * grant_title
        * reference
        * DR_scheme
        * funding_amount_usd
        * grant_start_date
        * RCR_log
        * RCR_log_above_threshold
        * time_since_first_pub (time from a publication to the first publication of that author)
        * max_time_since_first_pub (time from last to first publication)
        * years_between_first_last (years from first first author position to first last author position)

* `career_run_pipeline.py` can be used to run the whole pipeline

* `career_viz_calcs.py` is used for all calculations and data manipulation needed to create the visualisations

* `career_viz.py` creates the graph and the report html.