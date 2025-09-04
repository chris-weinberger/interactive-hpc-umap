"""
Single-file Dash app: UMAP with clickable flatmap SVG region selection
---------------------------------------------------------------------
Requirements (install):
    pip install dash dash-extensions plotly umap-learn numpy pandas

Expected files:
- average_connectome_data.csv (square matrix with region labels as index/columns)
- region_groupings.py (provides assign_group(region) -> group label)
- assets/rat_flatmap.svg  (preferred location for the flatmap)
  (fallback path used if not present: /mnt/data/rat_flatmap.svg)
- assets/style.css  (Dash auto-loads this)

Run:
    python app_umap_svg.py
Then open http://127.0.0.1:8080
"""

from __future__ import annotations

import os
import re
from typing import List

import numpy as np
import pandas as pd
import umap
import plotly.express as px

from dash import Dash, dcc, html, Input, Output, State, ctx
from dash_extensions import EventListener
from dash_dangerously_set_inner_html import DangerouslySetInnerHTML

from region_groupings import assign_group

# ----------------------
# Data loading & prep
# ----------------------
np.random.seed(42)

# Load your square connectivity matrix (index=regions, columns=regions)
df_average = pd.read_csv("./average_connectome_data.csv", header=0, index_col=0)

# Hippocampal regions (as provided in your original app)
hippocampal_regions = np.array(["DG", "CA3", "CA2", "CA1v", "CA1d", "SUBv", "SUBd"])

# FROM hippocampus (efferent)
df_avg_from = df_average[df_average.index.isin(hippocampal_regions)]

# TO hippocampus (afferent)
df_average_t = df_average.T
df_avg_to = df_average_t[df_average_t.index.isin(hippocampal_regions)]

# Drop HPC columns
df_avg_from = df_avg_from.drop(hippocampal_regions, axis=1)
df_avg_to = df_avg_to.drop(hippocampal_regions, axis=1)

# Keep only columns/rows with at least one nonzero connection (avoids empty dims)
df_avg_from = df_avg_from.loc[:, df_avg_from.apply(np.count_nonzero, axis=0) >= 1]
df_avg_to = df_avg_to.loc[:, df_avg_to.apply(np.count_nonzero, axis=0) >= 1]

regions_afferent: List[str] = list(df_avg_to.columns)
regions_efferent: List[str] = list(df_avg_from.columns)
all_regions_in_data: List[str] = sorted(set(regions_afferent).union(regions_efferent))

# Group labels
region_labels_afferent = [assign_group(r) for r in regions_afferent]
region_labels_efferent = [assign_group(r) for r in regions_efferent]

# ----------------------
# SVG loading & parsing
# ----------------------

def load_svg_text() -> str:
    """Try to load the flatmap SVG from ./assets first, then a known fallback."""
    candidates = [
        os.path.join("assets", "rat_flatmap.svg"),  # typical Dash assets path
        "/mnt/data/rat_flatmap.svg",  # dev fallback
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    raise FileNotFoundError(
        "rat_flatmap.svg not found. Place it in ./assets/rat_flatmap.svg"
    )


def sanitize_svg(svg_text: str) -> str:
    """Remove XML/DOCTYPE/<style> blocks and comments; return only the <svg>...</svg> section.
    This prevents CSS text from being rendered when we inject via Markdown.
    """
    s = svg_text
    # Remove XML declaration and DOCTYPE
    s = re.sub(r"<\?xml[^>]*?>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<!DOCTYPE[^>]*?>", "", s, flags=re.IGNORECASE)
    # Remove comments
    s = re.sub(r"<!--([\s\S]*?)-->", "", s)
    # Remove any inline <style>...</style> (often inside <defs>)
    s = re.sub(r"<style[\s\S]*?</style>", "", s, flags=re.IGNORECASE)
    # Sometimes <defs> only contains the style — drop empty defs
    s = re.sub(r"<defs>\s*</defs>", "", s, flags=re.IGNORECASE)
    # Keep only the outermost <svg>...</svg>
    start = s.find("<svg")
    end = s.rfind("</svg>")
    if start != -1 and end != -1:
        s = s[start:end + 6]
    return s


def ids_in_svg(svg_text: str) -> List[str]:
    # Capture all id="..." occurrences; keep unique
    ids = re.findall(r'id="([^"]+)"', svg_text)
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


# Load and sanitize SVG so it renders as HTML (not literal text)
svg_text = sanitize_svg(load_svg_text())
svg_ids = set(ids_in_svg(svg_text))
clickable_region_ids: List[str] = [r for r in all_regions_in_data if r in svg_ids]

initial_selection: List[str] = list(clickable_region_ids)

# ----------------------
# Dash app
# ----------------------
app = Dash(__name__)
app.title = "UMAP + Flatmap Region Selector"

# Events we want from the SVG clicks
CLICK_EVENTS = [
    {"event": "click", "props": [
        "target.id",
        "target.parentElement.id",
        "target.parentElement.parentElement.id",
        "target.parentNode.id",
        "currentTarget.id"
    ]}
]

app.layout = html.Div([
    html.H1("Interactive UMAP Viewer with Clickable Flatmap"),

    html.Div([
        html.Div([
            html.H3("Afferent Settings"),
            html.Label("n_neighbors"),
            dcc.Slider(id="n_neighbors_aff", min=2, max=10, step=1, value=3,
                       marks={i: str(i) for i in range(2, 11, 8)}),

            html.Label("min_dist", style={"marginTop": "10px"}),
            dcc.Slider(id="min_dist_aff", min=0.0, max=1.0, step=0.05, value=0.1,
                       marks={float(np.round(i, 2)): str(np.round(i, 2)) for i in np.arange(0.0, 1.05, 0.2)}),
        ], style={"width": "32%", "display": "inline-block", "verticalAlign": "top", "padding": "0 10px"}),

        html.Div([
            html.H3("Efferent Settings"),
            html.Label("n_neighbors"),
            dcc.Slider(id="n_neighbors_eff", min=2, max=20, step=1, value=10,
                       marks={i: str(i) for i in range(2, 21, 8)}),

            html.Label("min_dist", style={"marginTop": "10px"}),
            dcc.Slider(id="min_dist_eff", min=0.0, max=1.0, step=0.05, value=0.1,
                       marks={float(np.round(i, 2)): str(np.round(i, 2)) for i in np.arange(0.0, 1.05, 0.2)}),
        ], style={"width": "32%", "display": "inline-block", "verticalAlign": "top", "padding": "0 10px"}),

        html.Div([
            html.H3("Flatmap Region Selector"),
            html.Div([
                html.Button("Select all", id="btn_select_all", n_clicks=0, style={"marginRight": "6px"}),
                html.Button("Clear", id="btn_clear", n_clicks=0, style={"marginRight": "6px"}),
                html.Button("Invert", id="btn_invert", n_clicks=0),
                html.Div(id="selection_count", style={"marginTop": "6px", "fontStyle": "italic"}),
            ], style={"marginBottom": "8px"}),

            EventListener(
                id="svg_listener",
                events=CLICK_EVENTS,
                children=html.Div(
                    className="svg-wrap",
                    children=[
                        # Render sanitized SVG as raw HTML (clickable with ids)
                        dcc.Markdown(svg_text, dangerously_allow_html=True, id="svg_markdown"),
                    ],
                ),
                style={"border": "1px solid #ddd", "borderRadius": "8px", "padding": "8px", "maxHeight": "520px", "overflow": "auto"},
            ),
        ], style={"width": "36%", "display": "inline-block", "verticalAlign": "top", "padding": "0 10px"}),
    ]),

    html.Div([
        dcc.Graph(id="umap-plot-afferent", style={"display": "inline-block", "width": "49%"}),
        dcc.Graph(id="umap-plot-efferent", style={"display": "inline-block", "width": "49%"}),
    ], style={"marginTop": "12px"}),

    # Stores for selection logic
    dcc.Store(id="store_selected", data=initial_selection),
    dcc.Store(id="store_allowed", data=clickable_region_ids),

    # Dummy target for clientside DOM-highlighting side effects
    html.Div(id="svg_highlight_done", style={"display": "none"}),
])


# ----------------------
# Selection logic
# ----------------------
@app.callback(
    Output("store_selected", "data"),
    Input("svg_listener", "event"),
    Input("btn_clear", "n_clicks"),
    Input("btn_select_all", "n_clicks"),
    Input("btn_invert", "n_clicks"),
    State("store_selected", "data"),
    State("store_allowed", "data"),
    prevent_initial_call=True,
)
def update_selection(click_event, n_clear, n_all, n_invert, selected, allowed):
    trigger = ctx.triggered_id
    selected = list(selected or [])
    allowed = list(allowed or [])

    if trigger == "btn_clear":
        return []

    if trigger == "btn_select_all":
        return allowed

    if trigger == "btn_invert":
        return [rid for rid in allowed if rid not in set(selected)]

    if trigger == "svg_listener":
        if click_event:
            candidates = [
                click_event.get("target.id"),
                click_event.get("target.parentElement.id"),
                click_event.get("target.parentElement.parentElement.id"),
                click_event.get("target.parentNode.id"),
                click_event.get("currentTarget.id"),
            ]
            rid = next((c for c in candidates if isinstance(c, str) and c in allowed), None)
            if rid is not None:
                s = set(selected)
                if rid in s:
                    s.remove(rid)
                else:
                    s.add(rid)
                order = {r: i for i, r in enumerate(allowed)}
                return sorted(list(s), key=lambda r: order.get(r, 10**9))
    return selected


@app.callback(
    Output("selection_count", "children"),
    Input("store_selected", "data"),
    State("store_allowed", "data"),
)
def show_count(selected, allowed):
    selected = selected or []
    allowed = allowed or []
    return f"Selected {len(selected)} / {len(allowed)} regions"


# ----------------------
# UMAP plotting
# ----------------------
@app.callback(
    Output("umap-plot-afferent", "figure"),
    Output("umap-plot-efferent", "figure"),
    Input("n_neighbors_aff", "value"),
    Input("min_dist_aff", "value"),
    Input("n_neighbors_eff", "value"),
    Input("min_dist_eff", "value"),
    Input("store_selected", "data"),
)
def update_umap(n_neighbors_aff, min_dist_aff, n_neighbors_eff, min_dist_eff, selected_regions):
    # Afferent
    reducer_aff = umap.UMAP(n_neighbors=n_neighbors_aff, min_dist=min_dist_aff, random_state=42)
    emb_aff = reducer_aff.fit_transform(df_avg_to.T)
    df_aff = pd.DataFrame(emb_aff, columns=["x", "y"])
    df_aff["region"] = regions_afferent
    df_aff["group"] = region_labels_afferent

    if selected_regions:
        df_aff = df_aff[df_aff["region"].isin(selected_regions)]
    else:
        df_aff = df_aff.iloc[0:0]

    fig_aff = px.scatter(
        df_aff, x="x", y="y", color="group",
        hover_name="region",
        title=f"Afferent UMAP (n_neighbors={n_neighbors_aff}, min_dist={min_dist_aff})",
        color_discrete_sequence=px.colors.qualitative.Set1,
        width=700, height=500,
    )
    fig_aff.update_traces(marker=dict(size=8, opacity=0.85))

    if df_aff.empty:
        fig_aff.add_annotation(text="No regions selected", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig_aff.update_xaxes(visible=False).update_yaxes(visible=False)

    # Efferent
    reducer_eff = umap.UMAP(n_neighbors=n_neighbors_eff, min_dist=min_dist_eff, random_state=42)
    emb_eff = reducer_eff.fit_transform(df_avg_from.T)
    df_eff = pd.DataFrame(emb_eff, columns=["x", "y"])
    df_eff["region"] = regions_efferent
    df_eff["group"] = region_labels_efferent

    if selected_regions:
        df_eff = df_eff[df_eff["region"].isin(selected_regions)]
    else:
        df_eff = df_eff.iloc[0:0]

    fig_eff = px.scatter(
        df_eff, x="x", y="y", color="group",
        hover_name="region",
        title=f"Efferent UMAP (n_neighbors={n_neighbors_eff}, min_dist={min_dist_eff})",
        color_discrete_sequence=px.colors.qualitative.Set1,
        width=700, height=500,
    )
    fig_eff.update_traces(marker=dict(size=8, opacity=0.85))

    if df_eff.empty:
        fig_eff.add_annotation(text="No regions selected", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig_eff.update_xaxes(visible=False).update_yaxes(visible=False)

    return fig_aff, fig_eff


# ----------------------
# Clientside DOM highlighting
# ----------------------
app.clientside_callback(
    """
    function(selected, allowed){
        try {
            const root = document.getElementById('svg_markdown');
            if (!root) { return ''; }
            (allowed || []).forEach(function(id){
                const el = document.getElementById(id);
                if (el) {
                    el.classList.add('data-region');
                    el.classList.add('clickable-region');
                }
            });
            (allowed || []).forEach(function(id){
                const el = document.getElementById(id);
                if (el) el.classList.remove('selected');
            });
            (selected || []).forEach(function(id){
                const el = document.getElementById(id);
                if (el) el.classList.add('selected');
            });
        } catch (e) {}
        return '';
    }
    """,
    Output("svg_highlight_done", "children"),
    Input("store_selected", "data"),
    State("store_allowed", "data"),
)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
