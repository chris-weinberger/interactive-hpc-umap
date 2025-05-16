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
    html.H1("Interactive UMAP Viewer - afferent"),

    html.Div([
        html.Label("n_neighbors"),
        dcc.Slider(id='n_neighbors', min=2, max=20, step=1, value=15,
                   marks={i: str(i) for i in range(2, 21, 8)}),

        html.Label("min_dist", style={"marginTop": "20px"}),
        dcc.Slider(id='min_dist', min=0.0, max=1.0, step=0.05, value=0.1,
                   marks={round(i, 2): str(round(i, 2)) for i in np.arange(0.0, 1.05, 0.2)})
    ], style={'width': '50%', 'margin': 'auto'}),

    dcc.Graph(id='umap-plot')
])

@app.callback(
    Output('umap-plot', 'figure'),
    Input('n_neighbors', 'value'),
    Input('min_dist', 'value')
)
def update_umap(n_neighbors, min_dist):
    reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, random_state=42)
    embedding = reducer.fit_transform(df_avg_to.T)

    df = pd.DataFrame(embedding, columns=["x", "y"])
    df["region"] = regions_afferent
    df["group"] = region_labels_afferent

    fig = px.scatter(
        df, 
        x="x", 
        y="y", 
        color="group",
        hover_name="region",
        title=f"UMAP (n_neighbors={n_neighbors}, min_dist={min_dist})",
        color_discrete_sequence=px.colors.qualitative.Set1,
        width=800, height=600
    )
    fig.update_traces(marker=dict(size=8, opacity=0.75))
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
