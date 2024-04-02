# Wellcome Academic Graph Toolkit - IDR

## Description

This is the Interdisciplinary module of the Wellcome Academic Graph Toolkit. It makes use of the IDR class imported from the Wellcome Academic Graph Toolkit for an analysis of Discovery Researchers Portfolio (full technical results can be found [here](https://wellcomecloud.sharepoint.com/:w:/r/sites/Grp_Data_DataDigital/_layouts/15/Doc.aspx?sourcedoc=%7B108ED5C2-27CF-43B9-89BC-B98038F87499%7D&file=Narrative%20Report%20Draft.docx&action=default&mobileredirect=true)).

## Installation

Build the latest wheel of the wag_toolkit module. First install [python build](https://pypi.org/project/python-build/) and build module:

```bash
pip install python-build
python3 -m build
```

Once the new wheel is created, create (or update) the conda environment by running:

```bash
make setup
```

Refresh your shell, using the `bash` or `zsh` command depending on the shell you are using.

Activate the created conda environment

```shell

conda activate wellcome_academic_graph_toolkit

```

From this environment, load the necessary modules for the IDR pipeline:

```shell

pip install -r idr/requirements.txt

```

## Usage

The entire IDR pipeline can be run as:

```shell

python3 -m idr

```

The module usage is as follows:

```shell
usage: __main__.py [-h] [output_path] [parallel_cpus] [scheme_type_path] [award_mapping_path] [input_path]

Calculate diversity of Potfolio

positional arguments:
  output_path         folder to save analysis outputs.
  parallel_cpus       whether to utilise multiple cpu cores.
  scheme_type_path    location of scheme types metadata
  award_mapping_path  location of grant award metadata
  input_path          location of publication and grant dimension ids

```

The module executes the following stages of the analysis:

- Calculation of field similarity (cosine and citation-based) using reference list of DR publications.
- Calculation of all diversity scores (team, output and diffusion) using similarity matrix.
- Summary html reports on initial distributions of diversity and key statistics.
- Aggregating and merging to grant-level + additional summary reporting.
- Final viz's as htmls.

The summary html reports are used for data clearning in **aggregate_grant_level** where thresholds are made for data to include. When running this analysis again, thresholds should be updates accordingly. See the final viz's here:

- [idr_types](https://ds.wellcome.data/idr/dr/narrative/team_field_diversity.html)
- [subfield_treemap](https://ds.wellcome.data/idr/dr/narrative/subfield_treemap.html)
- [subfield_diversity](https://ds.wellcome.data/idr/dr/narrative/subfield_diversity.html)
