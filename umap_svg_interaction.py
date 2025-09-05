from pathlib import Path
import numpy as np
import pandas as pd
import umap
import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, html, dcc, Output, Input, State, no_update, callback_context
from dash_extensions import EventListener
from dash_dangerously_set_inner_html import DangerouslySetInnerHTML
from region_groupings import assign_group

# --- Load in connectomics data (No changes made here) ---
np.random.seed(42)
df_average = pd.read_csv('./data/average_connectome_data.csv', header=0, index_col=0)

hippocampal_regions = np.array(['DG','CA3','CA2','CA1v','CA1d','SUBv','SUBd'])
df_avg_from = df_average[df_average.index.isin(hippocampal_regions)]
df_average_t = df_average.T
df_avg_to = df_average_t[df_average_t.index.isin(hippocampal_regions)]
df_avg_from = df_avg_from.drop(hippocampal_regions, axis=1)
df_avg_to = df_avg_to.drop(hippocampal_regions, axis=1)
df_avg_from = df_avg_from.loc[:,df_avg_from.apply(np.count_nonzero, axis=0) >= 1]
df_avg_to = df_avg_to.loc[:,df_avg_to.apply(np.count_nonzero, axis=0) >= 1]

regions_afferent = list(df_avg_to.columns)
regions_efferent = list(df_avg_from.columns)

region_labels_afferent = [assign_group(r) for r in regions_afferent]
region_labels_efferent = [assign_group(r) for r in regions_efferent]

# Add these two functions after the data loading section

def create_initial_figure_aff(n_neighbors=3, min_dist=0.1, selected_regions=None):
    """Creates the initial afferent UMAP plot."""
    reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, random_state=42)
    embedding = reducer.fit_transform(df_avg_to.T)
    df_plot = pd.DataFrame(embedding, columns=["x", "y"])
    df_plot["region"] = regions_afferent
    df_plot["group"] = region_labels_afferent
    fig = px.scatter(
        df_plot, x="x", y="y", color="group", hover_name="region",
        title=f"Afferent UMAP (n={n_neighbors}, min_dist={min_dist})",
        color_discrete_sequence=px.colors.qualitative.Plotly,
        width=700, height=500
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
    return fig

def create_initial_figure_eff(n_neighbors=10, min_dist=0.1, selected_regions=None):
    """Creates the initial efferent UMAP plot."""
    reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, random_state=42)
    embedding = reducer.fit_transform(df_avg_from.T)
    df_plot = pd.DataFrame(embedding, columns=["x", "y"])
    df_plot["region"] = regions_efferent
    df_plot["group"] = region_labels_efferent
    fig = px.scatter(
        df_plot, x="x", y="y", color="group", hover_name="region",
        title=f"Efferent UMAP (n={n_neighbors}, min_dist={min_dist})",
        color_discrete_sequence=px.colors.qualitative.Plotly,
        width=700, height=500
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
    return fig

# --- Load SVG text ---
SVG_PATH = Path(__file__).parent / "assets" / "Edited_rat_flatmap.svg"
svg_text = SVG_PATH.read_text(encoding="utf-8")

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# --- App Layout ---
svg_dom = DangerouslySetInnerHTML(svg_text)
listener = EventListener(
    id="listener",
    children=html.Div(svg_dom, id="svg-root"),
    events=[{"event": "regionclick_simple", "props": ["detail"]}],
)

# --- App Layout (NEW VERSION) ---
app.layout = html.Div(
    [
        html.H1("Interactive Brain Connectivity Viewer"),

        # Main flex container for the two-column layout
        html.Div([

            # --- LEFT COLUMN ---
            html.Div([
                html.H2("Brain Flatmap — Region Select"),
                html.P("Click regions to toggle selection."),
                html.Div(
                    listener,
                    id="svg-container",
                    style={"border": "1px solid #ddd", "padding": "8px", "overflow": "hidden"},
                ),
                html.Hr(),
                # (Inside the Left Column)
                # Selection Info
                html.Div(
                    [
                        html.Div(["Last clicked: ", html.Strong(id="clicked-region", children="(none yet)")]),
                        html.Div(
                            [
                                html.Strong("Selected regions:"),
                                # NEW: A placeholder for the JavaScript to add the button.
                                html.Div(id='clear-btn-container', style={'marginLeft': '20px'})
                            ], 
                            style={'display': 'flex', 'alignItems': 'center'}
                        ),
                        html.Div(id="selected-chips", style={"marginTop": "8px"}),
                        dcc.Store(id="selected-store", data=[]),
                    ]
                ),
                html.Hr(),
                html.H2("UMAP Controls"),
                html.Div([
                    # Afferent Sliders
                    html.Div([
                        html.H3("Afferent Settings"),
                        html.Label("n_neighbors"),
                        dcc.Slider(id='n_neighbors_aff', min=2, max=10, step=1, value=3,
                                   marks={i: str(i) for i in range(2, 11, 2)}),
                        html.Label("min_dist", style={"marginTop": "10px"}),
                        dcc.Slider(id='min_dist_aff', min=0.0, max=1.0, step=0.05, value=0.1,
                                   marks={round(i, 2): str(round(i, 2)) for i in np.arange(0.0, 1.05, 0.2)})
                    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top', 'paddingRight': '4%'}),
                    
                    # Efferent Sliders
                    html.Div([
                        html.H3("Efferent Settings"),
                        html.Label("n_neighbors"),
                        dcc.Slider(id='n_neighbors_eff', min=2, max=20, step=1, value=10,
                                   marks={i: str(i) for i in range(2, 21, 3)}),
                        html.Label("min_dist", style={"marginTop": "10px"}),
                        dcc.Slider(id='min_dist_eff', min=0.0, max=1.0, step=0.05, value=0.1,
                                   marks={round(i, 2): str(round(i, 2)) for i in np.arange(0.0, 1.05, 0.2)})
                    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'})
                ]),
            ], style={'width': '48%', 'paddingRight': '2%'}), # End of Left Column

            # --- RIGHT COLUMN ---
            html.Div([
                html.H2("UMAP Projections"),
                # The plots now load with an initial figure, preventing a race condition
                dcc.Graph(id='umap-plot-afferent', figure=create_initial_figure_aff()),
                dcc.Graph(id='umap-plot-efferent', figure=create_initial_figure_eff())
            ], style={'flex': 1}), # End of Right Column

        ], style={'display': 'flex', 'flexDirection': 'row'}), # End of main flex container

    ],
    style={"fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif", "padding": "0px"},
)

# --- Callbacks ---

def chip(label: str):
    return html.Span(
        label,
        style={
            "display": "inline-flex", "alignItems": "center", "gap": "6px",
            "padding": "6px 10px", "margin": "4px", "border": "1px solid #ddd",
            "borderRadius": "999px", "fontSize": "12px", "background": "#f8f8f8",
            "userSelect": "none",
        },
    )

@app.callback(
    Output('umap-plot-afferent', 'figure'),
    Input('n_neighbors_aff', 'value'),
    Input('min_dist_aff', 'value'),
    Input('selected-store', 'data'),
    prevent_initial_call=True
)
def update_afferent_umap(n_neighbors, min_dist, selected_regions):
    """Updates the afferent UMAP plot when sliders or selections change."""
    reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, random_state=42)
    embedding = reducer.fit_transform(df_avg_to.T)
    
    df_plot_full = pd.DataFrame(embedding, columns=["x", "y"])
    df_plot_full["region"] = regions_afferent
    df_plot_full["group"] = region_labels_afferent

    selected_regions = selected_regions or []

    # --- Filter the DataFrame based on SVG selection ---
    if selected_regions:
        # If regions are selected, only show those in the plot.
        df_plot = df_plot_full[df_plot_full['region'].isin(selected_regions)].copy()
    else:
        # If no regions are selected, show all data.
        df_plot = df_plot_full

    fig = px.scatter(
        df_plot, x="x", y="y", color="group",
        hover_name="region",
        title=f"Afferent UMAP (n={n_neighbors}, min_dist={min_dist})",
        color_discrete_sequence=px.colors.qualitative.Plotly,
        width=700, height=500
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
    
    return fig

@app.callback(
    Output('umap-plot-efferent', 'figure'),
    Input('n_neighbors_eff', 'value'),
    Input('min_dist_eff', 'value'),
    Input('selected-store', 'data'),
    prevent_initial_call=True
)
def update_efferent_umap(n_neighbors, min_dist, selected_regions):
    """Updates the efferent UMAP plot when sliders or selections change."""
    reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, random_state=42)
    embedding = reducer.fit_transform(df_avg_from.T)

    df_plot_full = pd.DataFrame(embedding, columns=["x", "y"])
    df_plot_full["region"] = regions_efferent
    df_plot_full["group"] = region_labels_efferent

    selected_regions = selected_regions or []

    # --- Filter the DataFrame based on SVG selection ---
    if selected_regions:
        # If regions are selected, only show those in the plot.
        df_plot = df_plot_full[df_plot_full['region'].isin(selected_regions)].copy()
    else:
        # If no regions are selected, show all data.
        df_plot = df_plot_full

    fig = px.scatter(
        df_plot, x="x", y="y", color="group",
        hover_name="region",
        title=f"Efferent UMAP (n={n_neighbors}, min_dist={min_dist})",
        color_discrete_sequence=px.colors.qualitative.Plotly,
        width=700, height=500
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))

    return fig

@app.callback(
    Output("clicked-region", "children"),
    Output("selected-store", "data"),
    Output("selected-chips", "children"),
    Input("listener", "event"),
    State("selected-store", "data"),
    prevent_initial_call=True,
)
def on_region_click(evt, selected_store):
    """Handles clicks from the SVG to update the selection list."""
    if not evt or not isinstance(evt, dict):
        return no_update, no_update, no_update

    detail = evt.get("detail") or {}
    clicked = (detail.get("region_str") or "").strip()
    js_selected = detail.get("selected_labels")

    selected = list(selected_store or [])

    if isinstance(js_selected, list):
        selected = [str(x) for x in js_selected if str(x).strip()]
    else:
        if clicked:
            if clicked in selected:
                selected = [x for x in selected if x != clicked]
            else:
                selected = selected + [clicked]

    chips_children = [chip(lbl) for lbl in selected] if selected else [html.Span("(none selected yet)", style={"opacity": 0.6})]

    return (clicked or no_update), selected, chips_children


if __name__ == "__main__":
    app.run_server(debug=True, host="127.0.0.1", port=8050)