import numpy as np
import pandas as pd
import umap
import plotly.express as px
import re
from pathlib import Path

from dash import Dash, dcc, html
from dash import Input, Output, State, ctx, no_update
import dash_dangerously_set_inner_html as dhtml
from dash_dangerously_set_inner_html import DangerouslySetInnerHTML
from dash_extensions import EventListener

from region_groupings import assign_group


# =========================
# Load data
# =========================
np.random.seed(42)
df_average = pd.read_csv("./average_connectome_data.csv", header=0, index_col=0)

# Hippocampal regions
hippocampal_regions = np.array(['DG', 'CA3', 'CA2', 'CA1v', 'CA1d', 'SUBv', 'SUBd'])

# FROM hippocampus (efferent)
df_avg_from = df_average[df_average.index.isin(hippocampal_regions)]

# TO hippocampus (afferent)
df_average_t = df_average.T
df_avg_to = df_average_t[df_average_t.index.isin(hippocampal_regions)]

# Drop HPC columns
df_avg_from = df_avg_from.drop(hippocampal_regions, axis=1)
df_avg_to = df_avg_to.drop(hippocampal_regions, axis=1)

# Keep only columns/rows with >=1 nonzero connections
df_avg_from = df_avg_from.loc[:, df_avg_from.apply(np.count_nonzero, axis=0) >= 1]
df_avg_to   = df_avg_to.loc[:,   df_avg_to.apply(np.count_nonzero,   axis=0) >= 1]

regions_afferent = list(df_avg_to.columns)
regions_efferent = list(df_avg_from.columns)

region_labels_afferent = [assign_group(r) for r in regions_afferent]
region_labels_efferent = [assign_group(r) for r in regions_efferent]


# =========================
# SVG handling
# =========================
SVG_PATH = Path("assets/rat_flatmap.svg")
if not SVG_PATH.exists():
    raise FileNotFoundError("Could not find assets/rat_flatmap.svg. Make sure the file exists.")

BASE_SVG = SVG_PATH.read_text(encoding="utf-8")

def _normalize_svg_id(svg_id: str) -> str:
    """
    Map a clicked SVG element's id attribute to your region name.
    Adjust this if your SVG uses different id conventions.
    """
    if not svg_id:
        return ""
    # Examples of helpful normalizations:
    svg_id = svg_id.strip()
    svg_id = re.sub(r'^(aff-|eff-|roi-)', '', svg_id, flags=re.IGNORECASE)
    return svg_id

def _selected_css_selector(selected_regions):
    """
    Create a CSS :is() selector string like: :is(#CA1d, #CA1v, #DG)
    Only include IDs that are valid CSS identifiers (fallback: quote with escaping).
    """
    ids = []
    for r in selected_regions:
        # Basic sanitization for CSS id selector; if your ids have odd chars, adjust accordingly.
        safe = re.sub(r'[^a-zA-Z0-9_\-:.]', '\\\\', r)
        ids.append(f"#{safe}")
    if not ids:
        return ""
    return ":is(" + ", ".join(ids) + ")"

def _styled_svg(selected_aff, selected_eff):
    """
    Return the SVG content with injected <style> that:
      - makes regions clickable
      - highlights selected regions
    We highlight any element whose id matches a selected region (aff or eff).
    """
    selected_all = set(selected_aff or []) | set(selected_eff or [])
    selector = _selected_css_selector(sorted(selected_all))

    # CSS to ensure the shapes are clickable and highlighted
    style = f"""
    <style>
      /* Make it obvious things are interactive */
      svg * {{
        cursor: pointer;
      }}
      /* Ensure clicks land on paths even if fills are transparent */
      path, g, polygon, polyline, rect, circle, ellipse {{
        pointer-events: all;
      }}
      /* Highlight selected regions (tweak colors as desired) */
      {selector} {{
        filter: drop-shadow(0 0 1.5px rgba(0,0,0,0.4));
        stroke: #0074D9 !important;
        stroke-width: 2 !important;
        fill: #7FDBFF !important;
        fill-opacity: 0.7 !important;
      }}
      /* Optional: hover glow */
      svg *:hover {{
        filter: drop-shadow(0 0 1px rgba(0,0,0,0.3));
      }}
    </style>
    """

    # Inject <style> right after the opening <svg ...> tag if possible
    # Fallback: prepend style.
    if "<svg" in BASE_SVG:
        # Insert after first '>' from <svg ...>
        idx = BASE_SVG.find(">")
        if idx != -1:
            return BASE_SVG[:idx+1] + style + BASE_SVG[idx+1:]
    return style + BASE_SVG


# =========================
# App
# =========================
app = Dash(__name__)

# Event spec: we want the event target so we can read target.id in the callback.
events = [{"event": "click", "props": ["target"]}]

app.layout = html.Div([
    html.H1("Interactive UMAP Viewer"),

    html.Div([
        html.Div([
            html.H3("Afferent Settings"),
            html.Label("n_neighbors"),
            dcc.Slider(
                id='n_neighbors_aff', min=2, max=10, step=1, value=3,
                marks={i: str(i) for i in range(2, 11, 8)}
            ),

            html.Label("min_dist", style={"marginTop": "10px"}),
            dcc.Slider(
                id='min_dist_aff', min=0.0, max=1.0, step=0.05, value=0.1,
                marks={round(i, 2): str(round(i, 2)) for i in np.arange(0.0, 1.05, 0.2)}
            ),

        ], style={'width': '45%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0 20px'}),

        html.Div([
            html.H3("Efferent Settings"),
            html.Label("n_neighbors"),
            dcc.Slider(
                id='n_neighbors_eff', min=2, max=20, step=1, value=10,
                marks={i: str(i) for i in range(2, 21, 8)}
            ),

            html.Label("min_dist", style={"marginTop": "10px"}),
            dcc.Slider(
                id='min_dist_eff', min=0.0, max=1.0, step=0.05, value=0.1,
                marks={round(i, 2): str(round(i, 2)) for i in np.arange(0.0, 1.05, 0.2)}
            ),

        ], style={'width': '45%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0 20px'}),
    ]),

    # Inline SVG with click listener
    html.Div([
        html.H3("Rat flatmap (click to toggle regions)"),
        EventListener(
            id="rat-events",
            events=events,
            # We will update 'children' with the SVG+style so selections get highlighted
            children=dhtml.DangerouslySetInnerHTML(_styled_svg(regions_afferent, regions_efferent))
        ),
        html.Small("Tip: ensure each ROI in the SVG has an id that matches your region name.")
    ], style={"border": "1px solid #ddd", "padding": "8px", "margin": "10px 0"}),

    html.Div([
        dcc.Graph(id='umap-plot-afferent', style={'display': 'inline-block', 'width': '48%'}),
        dcc.Graph(id='umap-plot-efferent', style={'display': 'inline-block', 'width': '48%'})
    ])
])


# =========================
# Callbacks
# =========================
@app.callback(
    Output("region_select_aff", "value"),
    Output("region_select_eff", "value"),
    Input("rat-events", "event"),
    State("region_select_aff", "value"),
    State("region_select_eff", "value"),
    prevent_initial_call=True
)
def toggle_region_from_svg(click_event, aff_vals, eff_vals):
    """
    When the user clicks any element in the SVG, we look up event['target']['id'].
    If that id matches a region in either afferent or efferent lists, toggle it
    in the corresponding dropdown.
    """
    aff_vals = set(aff_vals or [])
    eff_vals = set(eff_vals or [])

    if not click_event:
        return sorted(aff_vals), sorted(eff_vals)

    target = click_event.get("target", {}) or {}
    raw_id = target.get("id", "")
    if not raw_id:
        return sorted(aff_vals), sorted(eff_vals)

    region = _normalize_svg_id(raw_id)

    # Prefer exact matches; if the same id appears in both lists, toggle both.
    if region in regions_afferent:
        if region in aff_vals:
            aff_vals.remove(region)
        else:
            aff_vals.add(region)

    if region in regions_efferent:
        if region in eff_vals:
            eff_vals.remove(region)
        else:
            eff_vals.add(region)

    return sorted(aff_vals), sorted(eff_vals)


@app.callback(
    Output("rat-events", "children"),
    Input("region_select_aff", "value"),
    Input("region_select_eff", "value"),
)
def recolor_svg(selected_aff, selected_eff):
    """
    Re-render the SVG with CSS that highlights currently selected regions.
    """
    return dhtml.DangerouslySetInnerHTML(_styled_svg(selected_aff or [], selected_eff or []))


@app.callback(
    Output('umap-plot-afferent', 'figure'),
    Output('umap-plot-efferent', 'figure'),
    Input('n_neighbors_aff', 'value'),
    Input('min_dist_aff', 'value'),
    Input('n_neighbors_eff', 'value'),
    Input('min_dist_eff', 'value'),
    Input('region_select_aff', 'value'),
    Input('region_select_eff', 'value'),
)
def update_umap(n_neighbors_aff, min_dist_aff, n_neighbors_eff, min_dist_eff,
                selected_regions_aff, selected_regions_eff):

    # --- Afferent ---
    reducer_aff = umap.UMAP(n_neighbors=n_neighbors_aff, min_dist=min_dist_aff, random_state=42)
    embedding_aff = reducer_aff.fit_transform(df_avg_to.T)
    df_aff = pd.DataFrame(embedding_aff, columns=["x", "y"])
    df_aff["region"] = regions_afferent
    df_aff["group"]  = region_labels_afferent
    df_aff_filtered  = df_aff[df_aff['region'].isin(selected_regions_aff or [])]

    fig_aff = px.scatter(
        df_aff_filtered, x="x", y="y", color="group", hover_name="region",
        title=f"Afferent UMAP (n_neighbors={n_neighbors_aff}, min_dist={min_dist_aff})",
        color_discrete_sequence=px.colors.qualitative.Set1, width=700, height=500
    )
    fig_aff.update_traces(marker=dict(size=8, opacity=0.75))

    # --- Efferent ---
    reducer_eff = umap.UMAP(n_neighbors=n_neighbors_eff, min_dist=min_dist_eff, random_state=42)
    embedding_eff = reducer_eff.fit_transform(df_avg_from.T)
    df_eff = pd.DataFrame(embedding_eff, columns=["x", "y"])
    df_eff["region"] = regions_efferent
    df_eff["group"]  = region_labels_efferent
    df_eff_filtered  = df_eff[df_eff['region'].isin(selected_regions_eff or [])]

    fig_eff = px.scatter(
        df_eff_filtered, x="x", y="y", color="group", hover_name="region",
        title=f"Efferent UMAP (n_neighbors={n_neighbors_eff}, min_dist={min_dist_eff})",
        color_discrete_sequence=px.colors.qualitative.Set1, width=700, height=500
    )
    fig_eff.update_traces(marker=dict(size=8, opacity=0.75))

    return fig_aff, fig_eff


if __name__ == '__main__':
    # app.run_server(debug=True)
    app.run(debug=True, host='0.0.0.0', port=8080)
