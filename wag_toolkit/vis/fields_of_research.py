import json
import os
import shutil
from datetime import datetime
from functools import partial
from pathlib import Path


class VisJS:
    """Functionality to generate vis.js network from nodes and edges.

    Attributes:
        vis_nodes(dict): Field of research nodes for each year, in vis.js format.
        vis_edges(list): Field of research edges in VisJS format.

    """

    def __init__(self):
        self.vis_nodes = {}
        self.vis_edges = []

    def _existing_edges(self, year):
        """Return already processed edges, filtered by year.

        Args:
            year(int): Publication year to filter by.

        Returns:
            list: Field of research tuples.

        """
        filtered_edges = list(filter(lambda e: e["year"] == str(year), self.vis_edges))
        if len(filtered_edges) > 0:
            return [[e["from"], e["to"]] for e in filtered_edges]
        else:
            return []

    def _format_edge_title(self, f1, f2, adj_matrix, directed):
        """Format edge title to display percentage when hovering over an edge.

        Args:
            f1(str): Field of research 1 ("from").
            f2(str): Field of research 2 ("to").
            adj_matrix(pd.DataFrame): Adjacency matrix of fields of research.

        Returns:
            str: Text displayed when hovering over an edge.

        """
        if directed:
            pct = adj_matrix.loc[f1, f2] / adj_matrix.loc[f1, "All"] * 100
            title = f"{pct:.2f}%"
        else:
            title = f"{f1} - {f2}: {int(adj_matrix.loc[f1, f2]):,}"
        return title

    def _format_node_size(self, for_name, adj_matrix, directed, node_count="All"):
        """Calculate node sizes correctly based on field of research count.
        For citations-based visualisations, both source and cited publication counts are considered.

        Args:
            for_name(str): Field of research.
            adj_matrix(pd.DataFrame): Adjacency matrix of fields of research.
            directed(bool): Whether the edges are directed (citations-based) or undirected
                (coauthorship-based).
            colname(str): Name of column containing total counts.

        """
        total = adj_matrix.loc[node_count, for_name]
        if directed and (for_name in adj_matrix.index):
            total += adj_matrix.loc[for_name, node_count]
        return total

    def _format_node_title(self, for_name, total, adj_matrix):
        """Format node title to display extra information when hovering over a node.

        Args:
            for_name(str): Field of research.
            total(int): Node count.
            adj_matrix(pd.DataFrame): Adjacency matrix of fields of research.

        Returns:
            str: Text displayed when hovering over a node.

        """
        title = f"{for_name}: Number of {self.node_source}: {int(total)}"
        if for_name in adj_matrix.index:
            pct = (
                adj_matrix.loc[for_name, for_name]
                / adj_matrix.loc[for_name, "All"]
                * 100
            )
            title += f", <b>{pct:.2f}%</b> within-{self.node_type} {self.edge_source}"
        return title

    def _get_node_and_edge_data(
        self,
        year,
        adj_matrix,
        node_colour,
        edge_colour,
        font,
        threshold,
        node_scaling,
        edge_scaling,
        directed,
        weight_edges_by_pct=False,
        funder=None,
        node_count="All",
    ):
        """Extract nodes and edges from a given adjacency matrix and convert into vis.js format.

        Args:
            year(int): Publication year.
            adj_matrix(pd.DataFrame): Adjacency matrix of fields of research.
            node_colour(dict): Node colour metadata in vis.js format.
            edge_colour(dict): Edge colour metadata in vis.js format.
            font(dict): Font metadata in vis.js format.
            threshold(int): Minimum edge count to include in visualisation.
            node_scaling(float): Scaling factor for node sizes.
            edge_scaling(float): Scaling factor for edge widths.
            directed(bool): Whether the edges are directed (citations-based) or undirected
                (coauthorship-based).
            weight_edges_by_pct(bool): Whether to use counts or percentages to calculate edge widths.
            funder(Optional[str]): Name of funder to filter by.
            node_count(str): Name of column containing total node counts.

        """
        nodes_to_add = set()
        for f1 in adj_matrix.index.drop(list(set(["All", node_count]))):
            for f2, count in adj_matrix.loc[f1].items():
                if (f2 != f1) and (f2 != "All"):
                    if count <= threshold:
                        continue
                    nodes_to_add.update([f1, f2])
                    existing_edges = self._existing_edges(year=year)
                    if funder is not None:
                        if [f1, f2] not in existing_edges:
                            continue
                    if not directed:
                        if len(existing_edges) > 0:
                            if set([f1, f2]) in [set(e) for e in existing_edges]:
                                continue

                    edge_weight = count
                    if weight_edges_by_pct:
                        edge_weight = adj_matrix.loc[f1, f2] / adj_matrix.loc[f1, "All"]

                    edge_title = self._format_edge_title(
                        f1=f1, f2=f2, adj_matrix=adj_matrix, directed=directed
                    )

                    edge = self._add_edge(
                        from_node=f1,
                        to_node=f2,
                        weight=edge_weight,
                        title=edge_title,
                        scaling=edge_scaling,
                        colour=edge_colour,
                        year=year,
                        suffix=funder,
                    )
                    self.vis_edges.append(edge)

        if funder is not None:
            nodes_to_add = nodes_to_add.intersection(
                {n["id"] for n in self.vis_nodes[str(year)]}
            )

        for n in nodes_to_add:
            total = self._format_node_size(
                for_name=n,
                adj_matrix=adj_matrix,
                directed=directed,
                node_count=node_count,
            )
            title = self._format_node_title(
                for_name=n, total=total, adj_matrix=adj_matrix
            )
            node = self._add_node(
                node_name=n,
                total=total,
                title=title,
                colour=node_colour,
                font=font,
                scaling=node_scaling,
                suffix=funder,
            )
            self.vis_nodes[str(year)].append(node)

    def _remove_duplicate_edges(self):
        """Removes duplicate edges in case of undirected edges, i.e., if
        there is an existing edge from f1 -> f2, the edge from f2 -> f1 will be
        removed.

        """
        existing_fields = []
        for e in self.vis_edges:
            fields = {e["from"], e["to"], e["year"]}
            if fields not in existing_fields:
                existing_fields.append(fields)
            else:
                self.vis_edges.remove(e)

    def load_visjs_nodes_and_edges(
        self,
        threshold=50,
        node_colour=None,
        edge_colour=None,
        font=None,
        node_scaling=0.0005,
        edge_scaling=0.001,
        funder_node_scaling=None,
        funder_edge_scaling=None,
        weight_edges_by_pct=False,
        directed=False,
        node_count="All",
    ):
        """Sets up JSON structure of nodes and edges for field of research interaction visualisation using vis.js.
        For specific formatting options, take a look at the vis.js documentation:
        Nodes: https://visjs.github.io/vis-network/docs/network/nodes.html
        Edges: https://visjs.github.io/vis-network/docs/network/edges.html.

        Args:
            threshold(int): Minimum edge count to include in visualisation.
            node_colour(Optional[dict]): Node colour metadata in vis.js format.
            edge_colour(Optional[dict]): Edge colour metadata in vis.js format.
            font(Optional[dict]): Font metadata in vis.js format.
            node_scaling(float): Scaling factor for node sizes.
            edge_scaling(float): Scaling factor for edge widths.
            weight_edges_by_pct(bool): Whether to use counts or percentages to calculate edge widths.
            directed(bool): Whether the edges are directed (citations-based) or undirected
                (coauthorship-based).

        """
        self.vis_nodes = {}
        self.vis_edges = []

        funders = {
            k
            for y in self.adjacency_matrices.keys()
            for k in list(self.adjacency_matrices[y].keys())
            if k != "All"
        }
        if funder_node_scaling is None:
            funder_node_scaling = node_scaling * 10
        if funder_edge_scaling is None:
            funder_edge_scaling = edge_scaling
            if not weight_edges_by_pct:
                funder_edge_scaling = edge_scaling * 10

        for year in self.adjacency_matrices.keys():
            if str(year) not in self.vis_nodes.keys():
                self.vis_nodes[str(year)] = []

                get_node_and_edge_data = partial(
                    self._get_node_and_edge_data,
                    year=year,
                    edge_colour=edge_colour,
                    node_colour=node_colour,
                    font=font,
                    weight_edges_by_pct=weight_edges_by_pct,
                    directed=directed,
                    node_count=node_count,
                )
            get_node_and_edge_data(
                adj_matrix=self.adjacency_matrices[year]["All"],
                node_scaling=node_scaling,
                edge_scaling=edge_scaling,
                threshold=threshold,
            )

            if len(funders) > 0:
                for funder in funders:
                    get_node_and_edge_data(
                        adj_matrix=self.adjacency_matrices[year][funder],
                        node_scaling=funder_node_scaling,
                        edge_scaling=funder_edge_scaling,
                        threshold=0,
                        funder=funder,
                    )
        if not directed:
            self._remove_duplicate_edges()

    @staticmethod
    def _add_node(node_name, total, title, colour, font, scaling, suffix=None):
        """Get node in vis.js format.

        Args:
            node_name(str): Field of research.
            total(int): Node count.
            title(str): Hover text.
            colour(dict): Node colour metadata in vis.js format.
            font(dict): Font metadata in vis.js format.
            scaling(float): Scaling factor for node size.
            suffix(Optional[str]): Funder suffix to add to node ID.

        Returns:
            dict: Node in vis.js format.

        """
        if font is None:
            font = {"size": 40, "face": "Helvetica Neue"}
        if colour is None:
            colour = {"background": "#3273F6", "highlight": "#f2aa02", "opacity": 0.9}

        id = node_name
        group = "All"
        if suffix:
            id += f"_{suffix}"
            group = suffix
        node = {
            "color": colour,
            "id": id,
            "font": font,
            "label": node_name,
            "shape": "dot",
            "size": 1 + total * scaling,
            "title": title,
            "group": group,
        }
        return node

    @staticmethod
    def _add_edge(
        from_node, to_node, weight, title, scaling, colour, year, suffix=None
    ):
        """Get edge in vis.js format.

        Args:
            from_node(str): Field of research ("from", or start node).
            to_node(str): Field of research ("to", or end node).
            weight(float|int): Edge weight.
            title(str): Hover text.
            scaling(float): Scaling factor for edge size.
            colour(dict): dge colour metadata in vis.js format.
            year(int): Publication year.
            suffix(Optional[str]): Funder suffix to add to node IDs.

        Returns:
            dict: Edge in vis.js format.

        """
        if colour is None:
            colour = {"color": "#3273F6", "highlight": "#f2aa02", "opacity": 0.6}
        if suffix:
            from_node += f"_{suffix}"
            to_node += f"_{suffix}"
        edge = {
            "from": from_node,
            "to": to_node,
            "width": 0.05 + weight * scaling,
            "year": str(year),
            "title": title,
        }
        if colour is not None:
            edge["color"] = colour
        return edge

    @staticmethod
    def _set_global_options(nodes_metadata, edges_metadata):
        """Setup a dictionary of global vis.js options.

        Args:
            nodes_metadata(Optional[dict]): Global options for nodes.
            edges_metadata(Optional[dict]): Global options for edges.

        Returns:
            dict: Global visualisation options in vis.js format.

        """
        options = {
            "configure": {"enabled": False},
            "nodes": {"borderWidth": 0, "opacity": 1},
            "edges": {"smooth": {"enabled": True, "type": "curvedCCW"}},
            "interaction": {
                "dragNodes": True,
                "hideEdgesOnDrag": False,
                "hideNodesOnDrag": False,
            },
            "physics": {
                "enabled": True,
                "repulsion": {
                    "centralGravity": 0.001,
                    "damping": 0.09,
                    "nodeDistance": 500,
                    "springConstant": 0.005,
                    "springLength": 500,
                },
                "solver": "repulsion",
                "stabilization": {
                    "enabled": True,
                    "fit": True,
                    "iterations": 1000,
                    "onlyDynamicEdges": False,
                    "updateInterval": 50,
                },
            },
        }
        if nodes_metadata is not None:
            options["nodes"].update(nodes_metadata)
        if edges_metadata is not None:
            options["edges"].update(edges_metadata)
        return options

    @staticmethod
    def _to_json(fname, data):
        """Save data to JSON.

        Args:
            fname(str): Filename.

        """
        with open(fname, "w") as fp:
            json.dump(data, fp)

    def to_visjs(
        self,
        dirname,
        nodes_metadata=None,
        edges_metadata=None,
        directed=True,
        template=None,
        vis_name=None
    ):
        """Create interactive visualisation of field of research network in vis.js.
        See here for global visualisation options: https://visjs.github.io/vis-network/docs/network/#options.

        Args:
            nodes_metadata(Optional[dict]): Global options for nodes.
            edges_metadata(Optional[dict]): Global options for edges.
            directed(bool): Whether the edges are directed, i.e. arrows (citations-based) or undirected
                (coauthorship-based).
            template(Optional[str]): Path to html template.
            vis_name(Optional[str]): Visualisation filename.

        """
        if template is None:
            template = "toolkit/vis/for_template.html"
        if vis_name is None:
            vis_name = "for_interactions"
        if directed:
            if edges_metadata is None:
                edges_metadata = {}
            edges_metadata["arrows"] = "to"
            edges_metadata["arrowStrikethrough"] = False
        options = self._set_global_options(nodes_metadata, edges_metadata)

        new_dirname = dirname
        os.makedirs(new_dirname, exist_ok=True)
        self._to_json(Path(new_dirname) / "nodes.json", self.vis_nodes)
        self._to_json(Path(new_dirname) / "edges.json", self.vis_edges)
        self._to_json(Path(new_dirname) / "options.json", options)
        self._to_json(Path(new_dirname) / "positions.json", {})
        shutil.copy(template, Path(new_dirname) / f"{vis_name}.html")
        # TODO: Some code to dump the dictionaries on public_ds together with the html template
