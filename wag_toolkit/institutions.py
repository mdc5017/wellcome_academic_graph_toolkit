from collections import Counter
from itertools import combinations
import pandas as pd
from tqdm import tqdm
import networkx as nx
import community as community_louvain  
import plotly.express as px
import plotly.graph_objects as go


from .utils import Neo4j
from .vis.fields_of_research import VisJS
from .locations import Locations


class Institutions(Locations):
    """Institutions network from Wellcome Academic Graph.

    Attributes:
        coauthorship_nodes(list): Author nodes.
        coauthorship_edges(dict): Coauthorship edges for each publication year.

    """

    def __init__(self, cypher_query, graph=False):
        Neo4j.__init__(self, cypher_query, graph)
        VisJS.__init__(self)

        self.node_source = "authors"
        self.edge_source = "coauthorships"
        self.node_type = "institution"

        self.coauthorship_edges = {}
        self.institution_names = None
        self.publication_data = None
        self.adjacency_matrices = {}


    def _clean_adjacency_matrix(self, year_adjacency_matrix):
        to_remove = ['total', 'All']
        df_clean = year_adjacency_matrix.drop(index=[x for x in to_remove if x in year_adjacency_matrix.index], errors='ignore')
        df_clean = df_clean.drop(columns=[x for x in to_remove if x in df_clean.columns], errors='ignore')

        return df_clean
    

    def extract_networks(self):
        self.G = {}
        for year in self.adjacency_matrices:
            year_adjacency_matrix = pd.DataFrame(self.adjacency_matrices[year]['All'])
            df_clean = self._clean_adjacency_matrix(year_adjacency_matrix)

            self.G[year] = nx.from_pandas_adjacency(df_clean)

    
    def calculate_centrality(self):
        self.centrality_dfs = {}

        for year, G in self.G.items():
        
            degree_centrality = nx.degree_centrality(G)
            betweenness_centrality = nx.betweenness_centrality(G)
            closeness_centrality = nx.closeness_centrality(G)
            eigenvector_centrality = nx.eigenvector_centrality(G, max_iter=1000)
            
            df_degree = pd.DataFrame.from_dict(degree_centrality, orient='index', columns=['degree_centrality'])
            df_betweenness = pd.DataFrame.from_dict(betweenness_centrality, orient='index', columns=['betweenness_centrality'])
            df_closeness = pd.DataFrame.from_dict(closeness_centrality, orient='index', columns=['closeness_centrality'])
            df_eigenvector = pd.DataFrame.from_dict(eigenvector_centrality, orient='index', columns=['eigenvector_centrality'])
            centrality_df = pd.concat([df_degree, df_betweenness, df_closeness, df_eigenvector], axis=1)
            self.centrality_dfs[year] = centrality_df


    def find_louvain_communities(self):
        self.louvain_communities = {}

        for year, G in self.G.items():
            partition = community_louvain.best_partition(G)
            partition_df = pd.DataFrame.from_dict(partition, orient='index', columns=['community'])
            partition_df.index.name = 'institution'
            partition_df.reset_index(inplace=True)
            self.louvain_communities[year] = partition_df


    def plot_louvain_communities(self):
       
        years = sorted(self.G.keys())

        fig = go.Figure()

        # Add traces for each year, only first year's traces visible initially
        for i, year in enumerate(years):
            G = self.G[year]
            partition_df = self.louvain_communities[year]
            partition = dict(zip(partition_df['institution'], partition_df['community']))

            pos = nx.spring_layout(G, seed=42)

            # Edge traces
            edge_x = []
            edge_y = []
            for u, v in G.edges():
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]

            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=0.5, color='#888'),
                hoverinfo='none',
                mode='lines',
                visible=(i == 0)  
            )
            fig.add_trace(edge_trace)

            num_communities = partition_df['community'].max() + 1
            colors = px.colors.qualitative.Safe
            palette = colors * (num_communities // len(colors) + 1)

            for community_id in range(num_communities):
                node_x = []
                node_y = []
                node_text = []
                for node in G.nodes():
                    if partition.get(node) == community_id:
                        x, y = pos[node]
                        node_x.append(x)
                        node_y.append(y)
                        node_text.append(node)

                node_trace = go.Scatter(
                    x=node_x, y=node_y,
                    mode='markers',
                    hoverinfo='text',
                    text=node_text,
                    name=f'Community {community_id}',
                    marker=dict(
                        color=palette[community_id],
                        size=10,
                        line_width=0.5
                    ),
                    visible=(i == 0)  
                )
                fig.add_trace(node_trace)

        buttons = []
        trace_index = 0
        year_trace_indices = {}

        for year in years:
            partition_df = self.louvain_communities[year]
            n_communities = partition_df['community'].max() + 1

            indices = [trace_index]  
            indices += list(range(trace_index + 1, trace_index + 1 + n_communities))
            year_trace_indices[year] = indices
            trace_index += 1 + n_communities

        for year in years:
            vis = [False] * len(fig.data)
            for idx in year_trace_indices[year]:
                vis[idx] = True
            buttons.append(dict(
                label=str(year),
                method="update",
                args=[{"visible": vis},
                    {"title": f"Louvain Communities (Interactive) - Year {year}"}]
            ))

        fig.update_layout(
            updatemenus=[dict(
                active=0,
                buttons=buttons,
                x=0,
                y=1.1,
                xanchor='left',
                yanchor='top'
            )],
            showlegend=True,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[dict(
                text="Use zoom and hover for details",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002
            )],
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False)
        )

        fig.show()

