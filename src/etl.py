# src/etl.py
import pandas as pd
import numpy as np

def load_data(path: str = "data/sold_data.csv") -> pd.DataFrame:
    df = pd.read_csv(path)

    df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")

    for c in ["PRICE","BEDS","BATHS","SQUARE FEET","LOT SIZE","YEAR BUILT","HOA/MONTH",
              "ZIP OR POSTAL CODE","DAYS ON MARKET"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


    for d in ["LISTING DATE","SOLD DATE"]:
        if d in df.columns:
            df[d] = pd.to_datetime(df[d], errors="coerce")


    if "PROPERTY TYPE" in df.columns:
        df["PROPERTY TYPE"] = df["PROPERTY TYPE"].fillna("Unknown")


    if "ZIP OR POSTAL CODE" in df.columns:
        df["ZIP OR POSTAL CODE"] = df["ZIP OR POSTAL CODE"].fillna(0).astype(int)


    if "BEDS" in df and "BATHS" in df:
        df["BATHS"] = df["BATHS"].fillna(0)
        df["BEDS"]  = df["BEDS"].fillna(0)
        df["BED BATH RATIO"] = df["BEDS"] / df["BATHS"].replace(0, 1)

    return df


def dataset_bounds(df: pd.DataFrame) -> dict:
    def rng(col):
        if col not in df or df[col].dropna().empty:
            return None, None
        return float(df[col].min()), float(df[col].max())

    b = {}
    b["price_min"], b["price_max"] = rng("PRICE")
    b["beds_min"],  b["beds_max"]  = rng("BEDS")
    b["baths_min"], b["baths_max"] = rng("BATHS")
    b["sqft_min"],  b["sqft_max"]  = rng("SQUARE FEET")
    return b



def zip_points(df: pd.DataFrame) -> pd.DataFrame:

    need = {"ZIP OR POSTAL CODE","LATITUDE","LONGITUDE"}
    if not need.issubset(df.columns):
        return pd.DataFrame(columns=["ZIP","LAT","LON","COUNT","MEDIAN_PRICE"])
    g = df.dropna(subset=list(need)).groupby("ZIP OR POSTAL CODE")
    out = pd.DataFrame({
        "ZIP": g.size().index.astype(int),
        "COUNT": g.size().values,
        "MEDIAN_PRICE": g["PRICE"].median().values if "PRICE" in df else np.nan,
        "LAT": g["LATITUDE"].median().values,
        "LON": g["LONGITUDE"].median().values,
    })
    return out.sort_values("COUNT", ascending=False).reset_index(drop=True)


def filter_inventory_zip_price_beds(df: pd.DataFrame, price_range, beds_min):
    dff = df.copy()
    if price_range and price_range[0] is not None:
        dff = dff[dff["PRICE"] >= float(price_range[0])]
    if price_range and price_range[1] is not None:
        dff = dff[dff["PRICE"] <= float(price_range[1])]
    if beds_min is not None:
        dff = dff[dff["BEDS"] >= float(beds_min)]
    return dff


def listings_by_zip(df: pd.DataFrame, zip_code: int) -> pd.DataFrame:
    dff = df[df["ZIP OR POSTAL CODE"] == int(zip_code)].copy()
    keep = [c for c in ["ADDRESS","ZIP OR POSTAL CODE","PROPERTY TYPE","BEDS","BATHS",
                        "SQUARE FEET","LOT SIZE","YEAR BUILT","PRICE","LATITUDE","LONGITUDE"] if c in dff.columns]
    return dff[keep].sort_values("PRICE").reset_index(drop=True)


def suggest_zips_by_filter(df: pd.DataFrame, price_range, beds_min, topn=12):
    dff = filter_inventory_zip_price_beds(df, price_range, beds_min)
    if dff.empty or "ZIP OR POSTAL CODE" not in dff.columns:
        return []
    vc = dff["ZIP OR POSTAL CODE"].value_counts().head(topn).index.astype(int).tolist()
    return vc


def comps_similares(df: pd.DataFrame, zip_code: int, beds: float, baths: float, sqft: float, topn=20):
    if "ZIP OR POSTAL CODE" not in df:
        return pd.DataFrame()
    d = df[df["ZIP OR POSTAL CODE"] == int(zip_code)].dropna(subset=["BEDS","BATHS","SQUARE FEET"])
    if d.empty:
        return pd.DataFrame()
  
    w_beds, w_baths, w_sqft = 1.0, 1.0, 1/800.0
    dist = (w_beds*(d["BEDS"]-beds).abs() + w_baths*(d["BATHS"]-baths).abs() + w_sqft*(d["SQUARE FEET"]-sqft).abs())
    d = d.assign(_dist=dist).sort_values("_dist").head(topn)
    keep = [c for c in ["ADDRESS","ZIP OR POSTAL CODE","PROPERTY TYPE","BEDS","BATHS","SQUARE FEET","PRICE","LATITUDE","LONGITUDE","YEAR BUILT"] if c in d.columns]
    return d[keep].reset_index(drop=True)


def market_snapshot(df: pd.DataFrame, zip_code: int) -> dict:
    """Pequeño resumen de mercado para el ZIP"""
    d = df[df["ZIP OR POSTAL CODE"] == int(zip_code)]
    if d.empty:
        return {"count":0,"med_price":None,"med_sqft":None,"med_dom":None}
    snap = {
        "count": int(len(d)),
        "med_price": float(d["PRICE"].median()) if "PRICE" in d else None,
        "med_sqft": float(d["SQUARE FEET"].median()) if "SQUARE FEET" in d else None,
        "med_dom": float(d["DAYS ON MARKET"].median()) if "DAYS ON MARKET" in d else None,
    }
    return snap
