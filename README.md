# Wellcome Academic Graph Toolkit

Toolkit for working with the Wellcome Academic Graph and associated analysis code.

## Initial Setup

Make sure [direnv](https://direnv.net/docs/installation.html) is installed on the machine, this will allow us to better control our environment variables in an isolated environment.

Direnv installation:

```bash

# On ubuntu (AWS EC2)
sudo apt-get install direnv

# On Mac
brew install direnv

```

Add direnv to shell:

```bash

# For bash
echo "eval \"$(direnv hook bash)\"" >> ~/.bashrc

# For zsh
echo "eval $(direnv hook zsh)" >> ~/.zshrc

```

Run the Makefile phony setup target. This will run commands to create the conda environment and set environment variables.

```shell

# For dev environment setup
make setup

```

Refresh your shell, using the `bash` or `zsh` command depending on the shell you are using.

Activate the created conda environment

```shell

conda activate wellcome_academic_graph_toolkit

```

Manually set the following environment variables, replacing `your_details_here` with your own details.

```shell

# Neo4j
echo "export NEO4J_USERNAME=\"your_neo4j_username\"" >> ~/.envrc

echo "export NEO4J_PASSWORD=\"your_neo4j_password\"" >> ~/.envrc

```
