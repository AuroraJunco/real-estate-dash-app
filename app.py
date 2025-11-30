import dash
from dash import Dash, dcc, html, Input, Output, State
from dash.dash_table import DataTable
import plotly.graph_objects as go

from src.etl import (
    load_data, dataset_bounds, zip_points,
    filter_inventory_zip_price_beds, listings_by_zip,
    suggest_zips_by_filter, comps_similares, market_snapshot
)
from src.model import ModelService
from src.graphics import (
    zip_map, comps_map,
    price_hist, sqft_vs_price_rich, add_prediction_marker,
    property_type_mix
)

df = load_data()
ms = ModelService(df)
bounds = dataset_bounds(df)

postal_list = sorted(df["ZIP OR POSTAL CODE"].dropna().unique().tolist()) if "ZIP OR POSTAL CODE" in df else []
type_list = sorted(df["PROPERTY TYPE"].dropna().unique().tolist()) if "PROPERTY TYPE" in df else []

zip_df_full = zip_points(df)
has_map_coords = not zip_df_full.empty

HERO_IMAGES = [f"/assets/Fotos/hero{i}.jpg" for i in range(1, 9)]

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

label = lambda txt: html.Label(
    txt,
    style={"display": "block", "fontWeight": "600", "marginBottom": "6px"}
)

card = lambda children: html.Div(children, className="card")


def chips(items, selected=None):
    if not items:
        return html.Span("Sin resultados", className="chip")
    return html.Div(
        className="chips",
        children=[
            html.Span(
                str(i),
                className="chip" + (
                    " chip--active"
                    if (selected is not None and int(i) == int(selected))
                    else ""
                ),
            )
            for i in items
        ],
    )


def contact_modal():
    return html.Div(
        id="sell-modal",
        className="modal",
        style={"display": "none"},
        children=[
            html.Div(
                className="modal-content",
                children=[
                    html.H3("Publica tu vivienda", className="section-title"),
                    html.P(
                        "Deja tus datos y te contactaremos para coordinar la venta.",
                        className="muted",
                    ),
                    label("Nombre completo"),
                    dcc.Input(id="sell-contact-name", type="text", className="input"),
                    label("Email"),
                    dcc.Input(id="sell-contact-email", type="email", className="input"),
                    label("Teléfono"),
                    dcc.Input(id="sell-contact-phone", type="text", className="input"),
                    label("Detalles de la casa"),
                    dcc.Textarea(
                        id="sell-contact-notes",
                        className="input",
                        style={"minHeight": "90px"},
                    ),
                    html.Div(
                        className="row mt",
                        children=[
                            html.Button(
                                "Cancelar",
                                id="sell-modal-cancel",
                                className="btn secondary",
                            ),
                            html.Button(
                                "Enviar",
                                id="sell-modal-send",
                                className="btn primary",
                            ),
                        ],
                    ),
                ],
            )
        ],
    )


hero = html.Div(
    id="hero",
    className="hero",
    children=[
        html.Div(className="hero-overlay"),
        html.Div(
            className="hero-content",
            children=[
                html.Div(
                    className="hero-topbar",
                    children=[
                        html.Div(
                            className="hero-logo",
                            children=[
                                html.Div("A. REAL ESTATE", className="logo-main"),
                            ],
                        ),
                        html.Div(
                            className="hero-menu",
                            children=[
                                html.Button(
                                    "QUIERO VENDER MI CASA",
                                    id="hero-sell-cta",
                                    className="btn hero-btn hero-btn--seller",
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    className="hero-center",
                    children=[
                        html.Div(
                            "Houston Real Estate Market", className="hero-kicker"
                        ),
                        html.Div(
                            "Nadie puede adivinar el precio perfecto ni el momento ideal para comprar o vender…",
                            className="hero-title",
                        ),
                        html.Div(
                            [
                                html.B("…menos mal que nosotros lo calculamos"),
                                html.Br(),
                                "Analizamos miles de datos reales del mercado inmobiliario para ayudarte a decidir con confianza",
                            ],
                            className="hero-subtitle",
                        ),
                        html.Div(
                            className="hero-cta-row",
                            children=[
                                html.Button(
                                    "SOY COMPRADOR",
                                    id="hero-go-buyer",
                                    className="btn hero-btn",
                                ),
                                html.Button(
                                    "SOY VENDEDOR",
                                    id="hero-go-seller",
                                    className="btn btn--ghost hero-btn",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)


def buyer_controls():
    return card(
        [
            html.H3("Filtra por precio y nº de habitaciones", className="section-title"),
            label("Rango de precio ($)"),
            dcc.RangeSlider(
                id="buy-price-range",
                min=int(bounds["price_min"]),
                max=int(bounds["price_max"]),
                step=5000,
                value=[int(bounds["price_min"]), int(bounds["price_max"])],
                marks={
                    int(bounds["price_min"]): f"${int(bounds['price_min']/1000)}k",
                    int(bounds["price_max"]): f"${int(bounds['price_max']/1000)}k",
                },
                tooltip={"always_visible": True, "placement": "bottom"},
            ),
            html.Div(id="buy-price-label", className="muted mt"),
            dcc.Input(
                id="buy-price-min",
                type="number",
                style={"display": "none"},
                value=int(bounds["price_min"]),
            ),
            dcc.Input(
                id="buy-price-max",
                type="number",
                style={"display": "none"},
                value=int(bounds["price_max"]),
            ),
            html.Div(
                className="row mt",
                children=[
                    html.Div(
                        className="half",
                        children=[
                            label("Dormitorios deseados"),
                            dcc.Dropdown(
                                id="buy-beds-min",
                                className="dropdown",
                                options=[
                                    {"label": f"{b} dormitorio(s)", "value": b}
                                    for b in range(
                                        int(bounds["beds_min"]),
                                        int(bounds["beds_max"]) + 1,
                                    )
                                ],
                                value=max(2, int(bounds["beds_min"])),
                                clearable=False,
                                placeholder="Elige nº de dormitorios",
                            ),
                        ],
                    ),
                    html.Div(
                        className="half",
                        children=[
                            label("ZIP preferido (opcional)"),
                            dcc.Dropdown(
                                id="buy-zip-pref",
                                className="dropdown",
                                options=[{"label": str(z), "value": int(z)} for z in postal_list],
                                placeholder="Selecciona un ZIP (opcional)",
                                clearable=True,
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(id="buy-warning", className="warn mt"),
        ]
    )


def buyer_map_and_table():
    return card(
        [
            html.H3("Mapa de zonas disponibles"),
            dcc.Graph(id="buy-map", figure=zip_map(zip_df_full), clear_on_unhover=True),
            html.Div(id="buy-available-zips", className="mt"),
            html.Hr(),
            html.H4("Viviendas del ZIP seleccionado"),
            DataTable(
                id="buy-table",
                columns=[
                    {"name": c, "id": c}
                    for c in [
                        "ADDRESS",
                        "ZIP OR POSTAL CODE",
                        "PROPERTY TYPE",
                        "BEDS",
                        "BATHS",
                        "SQUARE FEET",
                        "YEAR BUILT",
                        "PRICE",
                    ]
                ],
                data=[],
                page_size=8,
                row_selectable="single",
                style_cell={"textAlign": "center"},
                style_header={"fontWeight": "700"},
                style_table={"overflowX": "auto"},
            ),
        ]
    )


def buyer_offer_block():
    return card(
        [
            html.H3("Oferta recomendada"),
            html.Div(
                "Selecciona un punto del mapa (ZIP) y una vivienda de la tabla.",
                className="muted",
            ),
            html.Div(id="buy-offer-warn", className="warn mt"),
            html.Div(id="buy-offer-summary", className="badge-box mt"),
            html.Div(
                className="row",
                children=[
                    html.Div(dcc.Graph(id="buy-scatter"), className="half"),
                    html.Div(
                        className="half",
                        children=[
                            html.H4("Sugerencias para tu oferta"),
                            DataTable(
                                id="buy-scenarios",
                                columns=[
                                    {"name": "Opciones de precio", "id": "Escenario"},
                                    {"name": "Precio", "id": "Precio"},
                                    {"name": "Tiempo en mercado", "id": "Tiempo"},
                                ],
                                data=[],
                                page_size=5,
                                style_cell={"textAlign": "center"},
                                style_header={"fontWeight": "700"},
                            ),
                            html.Hr(),
                            html.Div(id="buy-peers", className="muted"),
                        ],
                    ),
                ],
            ),
        ]
    )


def seller_controls():
    zip_opts = [{"label": str(z), "value": z} for z in postal_list]
    ptype_opts = [{"label": str(p), "value": p} for p in type_list] if type_list else []
    subtitle = f"{len(postal_list)} ZIPs detectados en el dataset"
    default_ptype = type_list[0] if type_list else "Single Family Residential"
    zip_preview = html.Div(
        [html.Div("ZIPs disponibles (muestra):", className="muted"), chips(postal_list[:10])],
        className="zip-preview",
    )
    return card(
        [
            html.H3("Características de la vivienda"),
            html.Div(subtitle, className="muted"),
            zip_preview,
            label("ZIP"),
            dcc.Dropdown(
                id="sell-zip",
                options=zip_opts,
                placeholder="Selecciona ZIP del dataset",
                className="dropdown",
                searchable=True,
                optionHeight=35,
            ),
            label("Dormitorios"),
            dcc.Input(
                id="sell-beds",
                type="number",
                className="input",
                min=0,
                max=10,
                step=1,
                value=3,
            ),
            label("Baños"),
            dcc.Input(
                id="sell-baths",
                type="number",
                className="input",
                min=0,
                max=6,
                step=0.5,
                value=2,
            ),
            label("Superficie (ft2)"),
            dcc.Input(
                id="sell-sqft",
                type="number",
                className="input",
                min=200,
                max=8000,
                step=10,
                value=1600,
            ),
            label("Tipo de propiedad"),
            dcc.Dropdown(
                id="sell-ptype",
                options=ptype_opts,
                value=default_ptype,
                placeholder="Selecciona tipo de propiedad",
                className="dropdown",
                clearable=False,
            ),
            label("Lote (ft2)"),
            dcc.Input(
                id="sell-lot",
                type="number",
                className="input",
                min=0,
                max=30000,
                value=7000,
            ),
            label("Año"),
            dcc.Input(
                id="sell-year",
                type="number",
                className="input",
                min=1850,
                max=2050,
                value=1995,
            ),
            html.Div(id="sell-contact-banner", className="warn mt"),
            html.Button(
                "Quiero vender mi casa",
                id="sell-open-modal",
                className="btn primary mt",
            ),
            html.Div(id="sell-warn", className="warn mt"),
        ]
    )


def seller_results():
    return card(
        [
            html.H3("Estimación, mercado y comparables", className="section-title"),
            html.Div(id="sell-market", className="badge-box"),
            html.Div(id="sell-summary", className="badge-box mt"),
            html.Div(
                className="row mt",
                children=[html.Div(dcc.Graph(id="sell-comps-map"), className="col-100")],
            ),
            html.Div(
                className="row mt",
                children=[html.Div(dcc.Graph(id="sell-type-mix"), className="col-100")],
            ),
            html.Div(
                className="row mt",
                children=[html.Div(dcc.Graph(id="sell-hist"), className="col-100")],
            ),
            html.H4("Comparables cercanos"),
            DataTable(
                id="sell-comps-table",
                columns=[
                    {"name": c, "id": c}
                    for c in [
                        "ADDRESS",
                        "PROPERTY TYPE",
                        "BEDS",
                        "BATHS",
                        "SQUARE FEET",
                        "YEAR BUILT",
                        "PRICE",
                    ]
                ],
                data=[],
                page_size=8,
                style_cell={"textAlign": "center"},
                style_header={"fontWeight": "700"},
                style_table={"overflowX": "auto"},
            ),
        ]
    )


app.layout = html.Div(
    [
        dcc.Store(id="buy-selected-zip", data=None),
        dcc.Store(id="sell-modal-open", data=False),
        hero,
        dcc.Interval(id="hero-interval", interval=5000, n_intervals=0),
        dcc.Tabs(
            id="tabs",
            value="buyer",
            className="tabs-realestate",
            parent_className="tabs-realestate-wrap",
            children=[
                dcc.Tab(
                    label="COMPRADOR",
                    value="buyer",
                    className="tab-realestate",
                    selected_className="tab-realestate--active",
                    children=[
                        html.Div(
                            className="row mt-lg",
                            children=[
                                html.Div(buyer_controls(), className="col-30"),
                                html.Div(buyer_map_and_table(), className="col-70"),
                            ],
                        ),
                        html.Div(
                            className="row mt-lg",
                            children=[html.Div(buyer_offer_block(), className="col-100")],
                        ),
                    ],
                ),
                dcc.Tab(
                    label="VENDEDOR",
                    value="seller",
                    className="tab-realestate",
                    selected_className="tab-realestate--active",
                    children=[
                        html.Div(
                            className="row mt-lg",
                            children=[
                                html.Div(seller_controls(), className="col-30"),
                                html.Div(seller_results(), className="col-70"),
                            ],
                        )
                    ],
                ),
            ],
        ),
        contact_modal(),
    ],
    className="container",
)


@app.callback(
    Output("tabs", "value"),
    Input("hero-go-buyer", "n_clicks"),
    Input("hero-go-seller", "n_clicks"),
    prevent_initial_call=True,
)
def hero_go_to_tab(buyer_clicks, seller_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    trig = ctx.triggered[0]["prop_id"].split(".")[0]
    if trig == "hero-go-buyer":
        return "buyer"
    if trig == "hero-go-seller":
        return "seller"
    return dash.no_update


@app.callback(Output("hero", "style"), Input("hero-interval", "n_intervals"))
def update_hero_background(n):
    if not HERO_IMAGES:
        return dash.no_update
    idx = n % len(HERO_IMAGES)
    url = HERO_IMAGES[idx]
    bg = f"linear-gradient(135deg, rgba(0,0,0,0.55), rgba(0,0,0,0.35)), url('{url}')"
    return {
        "backgroundImage": bg,
        "backgroundSize": "cover",
        "backgroundPosition": "center",
    }


@app.callback(
    Output("hero-go-buyer", "style"),
    Output("hero-go-seller", "style"),
    Input("tabs", "value"),
)
def update_button_styles(active_tab):
    if active_tab == "buyer":
        buyer_style = {
            "backgroundColor": "#164d4f",
            "color": "white",
            "border": "none",
        }
        seller_style = {
            "backgroundColor": "transparent",
            "color": "white",
            "border": "2px solid white",
        }
    else:
        buyer_style = {
            "backgroundColor": "transparent",
            "color": "white",
            "border": "2px solid white",
        }
        seller_style = {
            "backgroundColor": "#164d4f",
            "color": "white",
            "border": "none",
        }
    return buyer_style, seller_style


@app.callback(
    Output("buy-price-min", "value"),
    Output("buy-price-max", "value"),
    Output("buy-price-label", "children"),
    Input("buy-price-range", "value"),
)
def sync_price_slider(price_range):
    if not price_range:
        return dash.no_update, dash.no_update, ""
    pmin, pmax = price_range
    label_txt = f"Seleccionado: ${int(pmin/1000)}k – ${int(pmax/1000)}k"
    return pmin, pmax, label_txt


@app.callback(
    Output("buy-map", "figure"),
    Output("buy-available-zips", "children"),
    Output("buy-warning", "children"),
    Input("buy-selected-zip", "data"),
    Input("buy-price-min", "value"),
    Input("buy-price-max", "value"),
    Input("buy-beds-min", "value"),
    Input("buy-zip-pref", "value"),
)
def buyer_update_map(selected_zip, price_min, price_max, beds_min, zip_pref):
    if not has_map_coords:
        fig_empty = go.Figure(layout=go.Layout(title="Mapa no disponible (faltan coordenadas)."))
        return fig_empty, "", ""

    price_min = float(price_min) if price_min is not None else bounds["price_min"]
    price_max = float(price_max) if price_max is not None else bounds["price_max"]
    price_range = [price_min, price_max]

    dff = filter_inventory_zip_price_beds(df, price_range, beds_min)
    zdf = zip_points(dff)

    warn = ""
    if zip_pref and (zdf.empty or zip_pref not in zdf["ZIP"].tolist()):
        sug = suggest_zips_by_filter(df, price_range, beds_min)
        warn = (
            f"No hay resultados en ZIP {zip_pref}. Sugerencias: {', '.join(map(str, sug))}"
            if sug
            else "No hay resultados para este filtro."
        )

    sel = selected_zip or zip_pref

    chips_div = html.Div(
        [
            html.Div("ZIPs con oferta en tu filtro", className="muted"),
            chips(zdf["ZIP"].tolist()[:12], selected=sel),
        ]
    )

    fig = zip_map(zdf, sel, "Zonas disponibles (click para seleccionar)")
    return fig, chips_div, warn


@app.callback(
    Output("buy-table", "data"),
    Output("buy-table", "selected_rows"),
    Input("buy-map", "clickData"),
    State("buy-price-min", "value"),
    State("buy-price-max", "value"),
    State("buy-beds-min", "value"),
)
def buyer_load_zip_table(clickData, price_min, price_max, beds_min):
    if not clickData:
        return [], []
    try:
        point = clickData["points"][0]
        if "customdata" in point and point["customdata"]:
            zip_clicked = int(point["customdata"][0])
        else:
            zip_clicked = int(point.get("hovertext"))
    except Exception:
        return [], []
    price_min = float(price_min) if price_min is not None else bounds["price_min"]
    price_max = float(price_max) if price_max is not None else bounds["price_max"]
    dff = filter_inventory_zip_price_beds(df, [price_min, price_max], beds_min)
    table = listings_by_zip(dff, zip_clicked)
    keep = [
        c
        for c in [
            "ADDRESS",
            "ZIP OR POSTAL CODE",
            "PROPERTY TYPE",
            "BEDS",
            "BATHS",
            "SQUARE FEET",
            "YEAR BUILT",
            "PRICE",
        ]
        if c in table.columns
    ]
    return table[keep].head(200).to_dict("records"), []


@app.callback(
    Output("buy-offer-warn", "children"),
    Output("buy-offer-summary", "children"),
    Output("buy-scatter", "figure"),
    Output("buy-scenarios", "data"),
    Output("buy-peers", "children"),
    Input("buy-table", "derived_virtual_data"),
    Input("buy-table", "selected_rows"),
)
def buyer_predict_offer(rows, selected_rows):
    if not rows or not selected_rows:
        return "", "", go.Figure(), [], ""
    row = rows[selected_rows[0]]
    zip_code = int(row.get("ZIP OR POSTAL CODE") or 0) if "ZIP OR POSTAL CODE" in row else None
    beds = float(row.get("BEDS") or 0)
    baths = float(row.get("BATHS") or 0)
    sqft = float(row.get("SQUARE FEET") or 0)
    year = float(row.get("YEAR BUILT") or 0)
    ptype = row.get("PROPERTY TYPE") or "Single Family Residential"
    used_approx = False
    try:
        f = ms.build_features(zip_code, beds, baths, sqft, 0, year, 0, ptype)
        base = ms.predict_price(f)
    except Exception:
        used_approx = True
        f = ms.build_features(zip_code, beds, baths, sqft, 0, year, 0, ptype)
        base = ms.predict_price(f)
    offer_min = base * 0.97
    warn = (
        "No hay datos suficientes o modelo entrenado para este caso; te mostramos una aproximación basada en estadística de la zona."
        if used_approx
        else ""
    )
    summary = html.Div(
        [
            html.Div(f"Precio base modelo/estimado: ${base:,.0f}", className="badge"),
            html.Div(f"Oferta recomendada (min): ${offer_min:,.0f}", className="badge success"),
        ],
        className="badge-row",
    )
    dzip = df[df["ZIP OR POSTAL CODE"] == zip_code] if zip_code else df
    fig = sqft_vs_price_rich(dzip, "Precio vs Superficie (detalle)")
    fig = add_prediction_marker(fig, sqft, base, "Predicción")
    if "ZIP OR POSTAL CODE" in dzip:
        fig.update_traces(customdata=dzip["ZIP OR POSTAL CODE"])
    mults = [0.90, 0.95, 1.00, 1.05, 1.10]
    precios_esc = [base * m for m in mults]
    ys = []
    for precio_opcion in precios_esc:
        try:
            feats_time = ms.build_features(
                zip_code,
                beds,
                baths,
                sqft,
                0,
                year,
                0,
                ptype,
            )
            if ms.has_time:
                cat = ms.predict_time_category(feats_time, precio_opcion)
            else:
                cat = 1
        except Exception:
            cat = 1
        ys.append(cat)
    if len(set(ys)) == 1:
        ys = [0, 0, 1, 2, 2]
    scen = [
        {
            "Escenario": f"{int(m * 100)}%",
            "Precio": f"${precios_esc[i]:,.0f}",
            "Tiempo": ms.time_label(ys[i]) if ms.has_time else (
                "<=30 días" if ys[i] == 0 else "31–60 días" if ys[i] == 1 else ">60 días"
            ),
        }
        for i, m in enumerate(mults)
    ]
    peers = dzip[(dzip["PRICE"] >= base * 0.9) & (dzip["PRICE"] <= base * 1.1)]
    if not peers.empty:
        peers_badges = html.Div(
            [
                html.Span(f"BEDS {beds:.1f} vs {peers['BEDS'].mean():.1f}", className="badge"),
                html.Span(f"BATHS {baths:.1f} vs {peers['BATHS'].mean():.1f}", className="badge"),
                html.Span(f"YEAR {year:.0f} vs {peers['YEAR BUILT'].median():.0f}", className="badge"),
                html.Span(f"ft2 {sqft:,.0f} vs {peers['SQUARE FEET'].median():.0f}", className="badge"),
            ],
            className="badge-row",
        )
        peer_msg = html.Div(
            [html.Div("Comparativa con pares (+/-10% del precio en el ZIP)", className="muted"), peers_badges]
        )
    else:
        peer_msg = "No hay suficientes pares en el ZIP para comparar."
    return warn, summary, fig, scen, peer_msg


@app.callback(
    Output("buy-selected-zip", "data"),
    Input("buy-map", "clickData"),
    Input("buy-scatter", "clickData"),
    Input("buy-table", "selected_rows"),
    State("buy-table", "derived_virtual_data"),
    prevent_initial_call=True,
)
def sync_selected_zip(map_click, scatter_click, sel_rows, table_rows):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    trig = ctx.triggered[0]["prop_id"].split(".")[0]
    if trig == "buy-map" and map_click:
        try:
            point = map_click["points"][0]
            if "customdata" in point and point["customdata"]:
                return int(point["customdata"][0])
            else:
                return int(point.get("hovertext"))
        except Exception:
            return dash.no_update
    if trig == "buy-table" and sel_rows and table_rows:
        row = table_rows[sel_rows[0]]
        if "ZIP OR POSTAL CODE" in row:
            return int(row["ZIP OR POSTAL CODE"] or 0)
    if trig == "buy-scatter" and scatter_click:
        try:
            return int(scatter_click["points"][0]["customdata"])
        except Exception:
            return dash.no_update
    return dash.no_update


@app.callback(
    Output("sell-warn", "children"),
    Output("sell-market", "children"),
    Output("sell-summary", "children"),
    Output("sell-type-mix", "figure"),
    Output("sell-hist", "figure"),
    Output("sell-comps-map", "figure"),
    Output("sell-comps-table", "data"),
    Input("sell-zip", "value"),
    Input("sell-beds", "value"),
    Input("sell-baths", "value"),
    Input("sell-sqft", "value"),
    Input("sell-ptype", "value"),
    Input("sell-lot", "value"),
    Input("sell-year", "value"),
)
def seller_infer(zip_code, beds, baths, sqft, ptype, lot, year):
    if not zip_code:
        return (
            "Selecciona un ZIP del listado.",
            "",
            "",
            go.Figure(),
            go.Figure(),
            go.Figure(),
            [],
        )
    if postal_list and zip_code not in postal_list:
        warn = f"ZIP {zip_code} fuera del dataset. Usa alguno de: {', '.join(map(str, postal_list[:10]))}"
        return (
            warn,
            "",
            "",
            go.Figure(),
            go.Figure(),
            go.Figure(),
            [],
        )
    snap = market_snapshot(df, zip_code)
    market = html.Div(
        [
            html.Div(f"Listado en ZIP {zip_code}", className="badge"),
            html.Div(f"Ventas analizadas: {snap['count']}", className="badge"),
            html.Div(
                f"Mediana precio: ${snap['med_price']:,.0f}"
                if snap["med_price"]
                else "Mediana precio: n/d",
                className="badge",
            ),
            html.Div(
                f"Mediana ft2: {snap['med_sqft']:,.0f}"
                if snap["med_sqft"]
                else "Mediana ft2: n/d",
                className="badge",
            ),
            html.Div(
                f"Mediana DOM: {snap['med_dom']:.0f}d" if snap["med_dom"] else "Mediana DOM: n/d",
                className="badge",
            ),
        ],
        className="badge-row",
    )
    comps = comps_similares(df, zip_code, beds or 0, baths or 0, sqft or 0)
    used_approx = False
    try:
        f = ms.build_features(zip_code, beds, baths, sqft, lot, year, 0, ptype)
        base = ms.predict_price(f)
        dom_cat = ms.predict_time_category(f, base) if ms.has_time else 1
    except Exception:
        used_approx = True
        f = ms.build_features(zip_code, beds, baths, sqft, lot, year, 0, ptype)
        base = ms.predict_price(f)
        dom_cat = 1
    dom_label = ms.time_label(dom_cat)
    warn = (
        "Resultado aproximado; no hay modelo entrenado/cobertura suficiente para este caso."
        if used_approx
        else ""
    )
    summary = html.Div(
        [
            html.Div(f"Precio estimado de salida: ${base:,.0f}", className="badge primary"),
            html.Div(f"Tiempo esperado: {dom_label}", className="badge info"),
            html.Div(f"Comparables usados: {len(comps)}", className="badge"),
        ],
        className="badge-row",
    )
    inv = df[df["ZIP OR POSTAL CODE"] == int(zip_code)]
    med_ppsf = (inv["PRICE"] / inv["SQUARE FEET"].replace(0, 1)).median() if not inv.empty else None
    ratio_bb = inv["BED BATH RATIO"].median() if "BED BATH RATIO" in inv else None
    metrics = html.Div(
        [
            html.Div(
                f"Mediana $/ft2: ${med_ppsf:,.0f}" if med_ppsf else "Mediana $/ft2: n/d",
                className="badge",
            ),
            html.Div(
                f"Ratio cama/baño mediana: {ratio_bb:.2f}"
                if ratio_bb
                else "Ratio cama/baño: n/d",
                className="badge",
            ),
        ],
        className="badge-row",
    )
    type_mix_fig = property_type_mix(inv, "Mix por tipo en el ZIP")
    hist_fig = price_hist(inv, "Distribución de precios en el ZIP")
    c_map = comps_map(comps, "Comparables cercanos")
    c_tbl = (
        comps[["ADDRESS", "PROPERTY TYPE", "BEDS", "BATHS", "SQUARE FEET", "YEAR BUILT", "PRICE"]].to_dict("records")
        if not comps.empty
        else []
    )
    return warn, market, html.Div([summary, metrics], className="badge-box"), type_mix_fig, hist_fig, c_map, c_tbl


@app.callback(
    Output("sell-modal", "style"),
    Output("sell-contact-banner", "children"),
    Output("sell-contact-name", "value"),
    Output("sell-contact-email", "value"),
    Output("sell-contact-phone", "value"),
    Output("sell-contact-notes", "value"),
    Input("sell-open-modal", "n_clicks"),
    Input("hero-sell-cta", "n_clicks"),
    Input("sell-modal-cancel", "n_clicks"),
    Input("sell-modal-send", "n_clicks"),
    State("sell-contact-name", "value"),
    State("sell-contact-email", "value"),
    State("sell-contact-phone", "value"),
    State("sell-contact-notes", "value"),
    prevent_initial_call=True,
)
def toggle_contact_modal(
    open_click,
    hero_open_click,
    cancel_click,
    send_click,
    name,
    email,
    phone,
    notes,
):
    ctx = dash.callback_context
    if not ctx.triggered:
        return (
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )
    trig = ctx.triggered[0]["prop_id"].split(".")[0]
    if trig in ("sell-open-modal", "hero-sell-cta"):
        return (
            {"display": "flex"},
            "",
            name, email, phone, notes,
        )
    if trig == "sell-modal-cancel":
        return (
            {"display": "none"},
            dash.no_update,
            name, email, phone, notes,
        )
    if trig == "sell-modal-send":
        thanks = f"Gracias {name or ''}. Nos pondremos en contacto con los datos enviados."
        return (
            {"display": "none"},
            thanks,
            "",
            "",
            "",
            "",
        )
    return (
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
    )


if __name__ == "__main__":
    app.run(debug=True)
