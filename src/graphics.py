# src/graphics.py

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


THEME_FONT = dict(family="Inter, Arial, sans-serif", color="#1f2933")
ACCENT = "#164d4f"
ACCENT_SOFT = "#6e8898"

# tema general para mantener los colores

def apply_theme(fig: go.Figure, title_text: str | None = None) -> go.Figure:

    warm_plot_bg = "#f3ece4"  
    grid_color = "rgba(180, 160, 140, 0.35)" 

    fig.update_layout(
        font=THEME_FONT,
        title=dict(
            text=title_text
            or (fig.layout.title.text if fig.layout.title.text is not None else ""),
            font=dict(
                family="Playfair Display, Georgia, serif",
                size=20,
                color=ACCENT,
            ),
            x=0.5,
            xanchor="center",
        ),
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor=warm_plot_bg,
        margin=dict(l=24, r=24, t=60, b=40),
        hoverlabel=dict(
            bgcolor="rgba(17,24,39,0.92)",
            font_size=11,
            font_family="Times New Roman, Georgia, serif",
        ),
    )

    fig.update_xaxes(showgrid=True, gridcolor=grid_color, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=grid_color, zeroline=False)
    return fig

# mapas

def zip_map(
    zip_df: pd.DataFrame,
    selected_zip: int | None = None,
    title: str = "Zonas disponibles (click para seleccionar)",
) -> go.Figure:

    if zip_df is None or zip_df.empty:
        return go.Figure(layout=go.Layout(title=title))


    warm_scale = ["#f7efe7", "#e8c9a9", "#d39b73", "#b56b45", "#7b3f27"]

    fig = px.scatter_mapbox(
        zip_df,
        lat="LAT",
        lon="LON",
        hover_name="ZIP",
        hover_data={
            "COUNT": True,
            "MEDIAN_PRICE": ":,.0f",
            "LAT": False,
            "LON": False,
            "ZIP": False,
        },
        custom_data=["ZIP", "COUNT", "MEDIAN_PRICE"],
        size="COUNT",
        color="MEDIAN_PRICE",
        color_continuous_scale=warm_scale,
        size_max=34,
        zoom=10,
        height=520,
        title=title,
    )

    fig.update_traces(
        marker=dict(opacity=0.88),
        hovertemplate=(
            "zip %{customdata[0]}<br>"
            "nº viviendas: %{customdata[1]}<br>"
            "precio medio: $%{customdata[2]:,.0f}"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=0, r=0, t=60, b=0),
        coloraxis_colorbar=dict(
            title=dict(text="Precio medio ($)", font=dict(size=13)),
            tickprefix="$",
        ),
        title=dict(
            text=title,
            font=dict(
                size=20,
                color=ACCENT,
                family="Playfair Display, Georgia, serif",
            ),
            x=0.5,
            xanchor="center",
        ),
        legend=dict(
            bgcolor="rgba(247,239,231,0.95)",
            bordercolor="rgba(15,23,42,0.08)",
            borderwidth=1,
            font=dict(size=12),
            orientation="h",
            yanchor="bottom",
            y=-0.12,
            xanchor="center",
            x=0.5,
        ),
        hoverlabel=dict(
            bgcolor="rgba(17,24,39,0.92)",
            font_size=11,
            font_family="Times New Roman, Georgia, serif",
        ),
    )



    if selected_zip is not None:
        sel = zip_df[zip_df["ZIP"] == int(selected_zip)]
        if not sel.empty:
            lat = sel["LAT"].values[0]
            lon = sel["LON"].values[0]


            fig.add_trace(
                go.Scattermapbox(
                    lat=[lat],
                    lon=[lon],
                    mode="markers",
                    marker=dict(
                        size=75,
                        color="rgba(255, 170, 170, 0.35)",
                    ),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )


            fig.add_trace(
                go.Scattermapbox(
                    lat=[lat],
                    lon=[lon],
                    mode="markers+text",
                    marker=dict(
                        size=38,
                        color="rgba(197, 132, 96, 0.9)",
                    ),
                    text=[f"ZIP {int(selected_zip)}"],
                    textposition="top right",
                    textfont=dict(
                        size=14,
                        color="#111827",
                        family="Times New Roman, Georgia, serif",
                    ),
                    name="Zona seleccionada",
                )
            )

    return fig



def comps_map(df: pd.DataFrame, title: str = "Comparables cercanos") -> go.Figure:

    if df is None or df.empty or not {"LATITUDE", "LONGITUDE"}.issubset(df.columns):
        return go.Figure(layout=go.Layout(title=title))

    warm_scale = ["#f7efe7", "#e8c9a9", "#d39b73", "#b56b45", "#7b3f27"]

    fig = px.scatter_mapbox(
        df,
        lat="LATITUDE",
        lon="LONGITUDE",
        hover_name="ADDRESS" if "ADDRESS" in df.columns else None,
        hover_data={
            "PRICE": ":,.0f",
            "BEDS": True,
            "BATHS": True,
            "SQUARE FEET": True,
        },
        color="PRICE" if "PRICE" in df.columns else None,
        color_continuous_scale=warm_scale,
        size="SQUARE FEET" if "SQUARE FEET" in df.columns else None,
        size_max=26,
        zoom=10,
        height=520,
        title=title,
    )

    fig.update_traces(
        marker=dict(opacity=0.9),
        hovertemplate=(
            "%{hovertext}<br>"
            "precio: $%{customdata[0]:,.0f}<br>"
            "dormitorios: %{customdata[1]}<br>"
            "baños: %{customdata[2]}<br>"
            "superficie: %{customdata[3]} ft²"
            "<extra></extra>"
        )
        if fig.data and hasattr(fig.data[0], "customdata")
        else None,
    )

    fig.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=0, r=0, t=60, b=0),
        coloraxis_colorbar=dict(
            title=dict(text="Precio ($)", font=dict(size=13)),
            tickprefix="$",
        ),
        title=dict(
            text=title,
            font=dict(
                size=20,
                color=ACCENT,
                family="Playfair Display, Georgia, serif",
            ),
            x=0.5,
            xanchor="center",
        ),
        hoverlabel=dict(
            bgcolor="rgba(17,24,39,0.92)",
            font_size=11,
            font_family="Times New Roman, Georgia, serif",
        ),
    )
    return fig



def price_hist(df: pd.DataFrame, title: str = "Distribución de precios") -> go.Figure:

    if df is None or df.empty:
        return go.Figure(layout=go.Layout(title=title))

    fig = px.histogram(
        df,
        x="PRICE",
        nbins=25,
        title=title,
        color_discrete_sequence=["#b56b45"],  # terracota
    )
    fig.update_layout(
        bargap=0.07,
        xaxis_title="Precio ($)",
        yaxis_title="Nº viviendas",
    )
    return apply_theme(fig, title)


def sqft_vs_price_rich(
    df: pd.DataFrame, title: str = "Precio vs superficie"
) -> go.Figure:

    if df is None or df.empty:
        return go.Figure(layout=go.Layout(title=title))

    hover = {
        "BEDS": True,
        "BATHS": True,
        "YEAR BUILT": True,
        "SQUARE FEET": True,
        "PRICE": ":,.0f",
        "PROPERTY TYPE": True,
    }

    warm_qualitative = ["#b56b45", "#7b3f27", "#e8c9a9", "#6e8898", "#cfa686"]

    fig = px.scatter(
        df,
        x="SQUARE FEET",
        y="PRICE",
        color="PROPERTY TYPE",
        size="BATHS" if "BATHS" in df.columns else None,
        hover_data=hover,
        trendline="ols",
        title=title,
        color_discrete_sequence=warm_qualitative,
    )

    fig.update_traces(
        marker=dict(
            opacity=0.86,
            line=dict(width=0.5, color="rgba(15,23,42,0.4)"),
        )
    )
    fig.update_xaxes(title="Superficie (ft²)")
    fig.update_yaxes(title="Precio ($)")
    fig.update_layout(legend_title_text="Tipo de propiedad")
    return apply_theme(fig, title)


def add_prediction_marker(
    fig: go.Figure, sqft: float, price: float, label: str = "Predicción"
) -> go.Figure:

    if fig is None:
        fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=[sqft],
            y=[price],
            mode="markers+text",
            marker=dict(
                size=16,
                symbol="star",
                color="#111827",
                line=dict(width=2, color="#fde047"),
            ),
            text=[label],
            textposition="top center",
            name=label,
        )
    )
    return fig


def property_type_mix(
    df: pd.DataFrame, title: str = "Mix por tipo de vivienda"
) -> go.Figure:
    if df is None or df.empty or "PROPERTY TYPE" not in df.columns:
        return go.Figure(layout=go.Layout(title=title))

    s = (
        df["PROPERTY TYPE"]
        .value_counts(normalize=True)
        .sort_values(ascending=False)
        * 100
    )

    warm_qualitative = ["#b56b45", "#7b3f27", "#e8c9a9", "#6e8898", "#cfa686"]

    fig = go.Figure(
        [
            go.Bar(
                x=s.index,
                y=s.values,
                marker=dict(color=warm_qualitative[: len(s)]),
            )
        ]
    )
    fig.update_layout(
        title=title,
        xaxis_title="Tipo de propiedad",
        yaxis_title="Inventario (%)",
    )
    return apply_theme(fig, title)




def price_time_curve(xs, ys, title: str = "Tiempo esperado según precio") -> go.Figure:

    if not xs or not ys:
        return go.Figure(layout=go.Layout(title=title))

    fig = go.Figure()


    bands = [
        {"cat": 0, "label": "<=30d", "color": "rgba(148, 215, 177, 0.25)"},
        {"cat": 1, "label": "31-60d", "color": "rgba(234, 200, 121, 0.25)"},
        {"cat": 2, "label": ">60d", "color": "rgba(197, 132, 96, 0.22)"},
    ]
    for b in bands:
        fig.add_shape(
            type="rect",
            x0=min(xs),
            x1=max(xs),
            y0=b["cat"] - 0.5,
            y1=b["cat"] + 0.5,
            fillcolor=b["color"],
            line=dict(width=0),
            layer="below",
        )

    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            line=dict(color="#b56b45", width=3),
            marker=dict(size=9, color="#111827"),
            name="% de precio",
            hovertemplate="precio: $%{x:,.0f}<br>tiempo (categoría): %{y}<extra></extra>",
        )
    )

    fig.update_yaxes(
        tickvals=[0, 1, 2],
        ticktext=["<=30 días", "31-60 días", ">60 días"],
        range=[-0.4, 2.4],
        title="Tiempo estimado",
    )
    fig.update_xaxes(title="Precio ($)")
    fig.update_layout(
        title=title,
        margin=dict(l=24, r=24, t=60, b=40),
        showlegend=False,
        height=360,
    )
    return apply_theme(fig, title)


