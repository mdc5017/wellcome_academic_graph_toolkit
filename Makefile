# Arcane incantation to print all the other targets, from https://stackoverflow.com/a/26339924
help:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'

.PHONY: conda-update
conda-update:
	# Build conda environment
	conda update conda
	conda env update --prune -f environment.yml
	@echo "!!!RUN THE conda activate wellcome_academic_graph COMMAND ABOVE RIGHT NOW!!!"

.PHONY: set_env_vars
set_env_vars:
	# Append development Neo4j environment variables to .envrc file
	echo "export NEO4J_BOLT_URL_DEV=\"bolt+ssc://neo4j.ops.wellcome.data:7687\"" >> .envrc
	echo "export NEO4J_BOLT_URL_PROD=\"bolt+ssc://n4j-prod.ops.wellcome.data:7687\"" >> .envrc
	direnv allow

.PHONY: setup
setup: set_env_vars conda-update