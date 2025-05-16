import numpy as np
import pandas as pd
import umap
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
from region_groupings import assign_group


# -------- Sample Data (replace this with your real data) --------
np.random.seed(42)
df_average = pd.read_csv('./average_connectome_data.csv', header=0, index_col=0)

# filter the afferent / efferent based on hippocampal connections, create similarity matrix
hippocampal_regions = np.array(['DG','CA3','CA2','CA1v','CA1d','SUBv','SUBd'])

# FROM hippocampus (efferent)
df_avg_from = df_average[df_average.index.isin(hippocampal_regions)]

# TO hippocampus (afferent)
df_average_t = df_average.T
df_avg_to = df_average_t[df_average_t.index.isin(hippocampal_regions)]

# drop HPC columns
df_avg_from = df_avg_from.drop(hippocampal_regions, axis=1)
df_avg_to = df_avg_to.drop(hippocampal_regions, axis=1)

# filter to only include columns and rows with at least one connection
df_avg_from = df_avg_from.loc[:,df_avg_from.apply(np.count_nonzero, axis=0) >= 1]
df_avg_to = df_avg_to.loc[:,df_avg_to.apply(np.count_nonzero, axis=0) >= 1]


regions_afferent = list(df_avg_to.columns)
regions_efferent = list(df_avg_from.columns)

region_labels_afferent = [assign_group(r) for r in regions_afferent]
region_labels_efferent = [assign_group(r) for r in regions_efferent]

# -------- Dash App --------
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Interactive UMAP Viewer"),

    html.Div([
        html.Div([
            html.H3("Afferent Settings"),
            html.Label("n_neighbors"),
            dcc.Slider(id='n_neighbors_aff', min=2, max=10, step=1, value=3,
                       marks={i: str(i) for i in range(2, 11, 8)}),

            html.Label("min_dist", style={"marginTop": "10px"}),
            dcc.Slider(id='min_dist_aff', min=0.0, max=1.0, step=0.05, value=0.1,
                       marks={round(i, 2): str(round(i, 2)) for i in np.arange(0.0, 1.05, 0.2)})
        ], style={'width': '45%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0 20px'}),

        html.Div([
            html.H3("Efferent Settings"),
            html.Label("n_neighbors"),
            dcc.Slider(id='n_neighbors_eff', min=2, max=20, step=1, value=10,
                       marks={i: str(i) for i in range(2, 21, 8)}),

            html.Label("min_dist", style={"marginTop": "10px"}),
            dcc.Slider(id='min_dist_eff', min=0.0, max=1.0, step=0.05, value=0.1,
                       marks={round(i, 2): str(round(i, 2)) for i in np.arange(0.0, 1.05, 0.2)})
        ], style={'width': '45%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0 20px'})
    ]),

    html.Div([
        dcc.Graph(id='umap-plot-afferent', style={'display': 'inline-block', 'width': '48%'}),
        dcc.Graph(id='umap-plot-efferent', style={'display': 'inline-block', 'width': '48%'})
    ])
])

@app.callback(
    Output('umap-plot-afferent', 'figure'),
    Output('umap-plot-efferent', 'figure'),
    Input('n_neighbors_aff', 'value'),
    Input('min_dist_aff', 'value'),
    Input('n_neighbors_eff', 'value'),
    Input('min_dist_eff', 'value')
)

def update_umap(n_neighbors_aff, min_dist_aff, n_neighbors_eff, min_dist_eff):
    reducer_aff = umap.UMAP(n_neighbors=n_neighbors_aff, min_dist=min_dist_aff, random_state=42)
    embedding_aff = reducer_aff.fit_transform(df_avg_to.T)
    df_aff = pd.DataFrame(embedding_aff, columns=["x", "y"])
    df_aff["region"] = regions_afferent
    df_aff["group"] = region_labels_afferent

    reducer_eff = umap.UMAP(n_neighbors=n_neighbors_eff, min_dist=min_dist_eff, random_state=42)
    embedding_eff = reducer_eff.fit_transform(df_avg_from.T)
    df_eff = pd.DataFrame(embedding_eff, columns=["x", "y"])
    df_eff["region"] = regions_efferent
    df_eff["group"] = region_labels_efferent

    fig_aff = px.scatter(
            df_aff, x="x", y="y", color="group",
            hover_name="region",
            title=f"Afferent UMAP (n_neighbors={n_neighbors_aff}, min_dist={min_dist_aff})",
            color_discrete_sequence=px.colors.qualitative.Set1,
            width=700, height=500
        )
    fig_aff.update_traces(marker=dict(size=8, opacity=0.75))

    fig_eff = px.scatter(
        df_eff, x="x", y="y", color="group",
        hover_name="region",
        title=f"Efferent UMAP (n_neighbors={n_neighbors_eff}, min_dist={min_dist_eff})",
        color_discrete_sequence=px.colors.qualitative.Set1,
        width=700, height=500
    )
    fig_eff.update_traces(marker=dict(size=8, opacity=0.75))

    return fig_aff, fig_eff

if __name__ == '__main__':
    # app.run_server(debug=True)
    app.run(debug=True, host='0.0.0.0', port=8080)
