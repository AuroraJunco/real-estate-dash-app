
# src/model.py
import os, json, pickle
import pandas as pd


PRICE_MODEL = "models/price_xgb.pkl"
TIME_MODEL  = "models/time_knn.pkl"
COLS_PRICE  = "models/feature_cols_model1.json"
COLS_TIME   = "models/feature_cols_model2.json"
SCALER_TIME = "models/scaler_time.pkl"

def _pickle_load(path: str):

    with open(path, "rb") as f:
        return pickle.load(f)


class ModelService:
    """
    Predicción de dos posibilidades según si hay datos de modelo:
    - Con modelo: usa los .pkl y columnas .json si estan presentes
    - Sin modelo: predicciones basadas en medianas y lógica
    El objetivo es que siempre pueda predecir algo razonable con lo que ponga el ususario
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._load_assets()

        if "ZIP OR POSTAL CODE" in self.df and "PRICE" in self.df:
            self.median_by_zip = self.df.groupby("ZIP OR POSTAL CODE")["PRICE"].median().to_dict()
        else:
            self.median_by_zip = {}
        self.global_median = float(self.df["PRICE"].median()) if "PRICE" in self.df else 0.0
        self.default_ptype = (
            self.df["PROPERTY TYPE"].mode()[0]
            if "PROPERTY TYPE" in self.df and not self.df["PROPERTY TYPE"].empty
            else "Single Family Residential"
        )

    def _load_assets(self):
        self.price_model = _pickle_load(PRICE_MODEL)
        self.time_model  = _pickle_load(TIME_MODEL)
        self.scaler_time = _pickle_load(SCALER_TIME)

        self.price_cols = json.load(open(COLS_PRICE)) if os.path.exists(COLS_PRICE) else []
        self.time_cols  = json.load(open(COLS_TIME))  if os.path.exists(COLS_TIME)  else []

        self.has_price = self.price_model is not None and len(self.price_cols) > 0
        self.has_time  = self.time_model  is not None and len(self.time_cols)  > 0


    def build_features(self, zip_code, beds, baths, sqft, lot, year, hoa, property_type, price_for_time=None):
        return pd.DataFrame([{
            "ZIP OR POSTAL CODE": int(zip_code) if zip_code is not None else 0,
            "BEDS": float(beds or 0),
            "BATHS": float(baths or 0),
            "SQUARE FEET": float(sqft or 0),
            "LOT SIZE": float(lot or 0),
            "YEAR BUILT": float(year or 0),
            "HOA/MONTH": float(hoa or 0),
            "BED BATH RATIO": (float(beds or 0) / (float(baths) if baths else 1.0)),
            "PRICE": float(price_for_time or 0),
            "PROPERTY TYPE": (property_type or self.default_ptype)
        }])

    def _align(self, df_in, target_cols):
        df_num = df_in.select_dtypes(include=["number"]).copy()
        dummies = pd.get_dummies(df_in[["PROPERTY TYPE"]], prefix=["property_type"])
        X = pd.concat([df_num, dummies], axis=1)
        for c in target_cols:
            if c not in X.columns:
                X[c] = 0
        return X[target_cols]


    def predict_price(self, feats_df: pd.DataFrame) -> float:
        if self.has_price:
            X = self._align(feats_df, self.price_cols)
            return float(self.price_model.predict(X)[0])

        zip_code = int(feats_df.iloc[0]["ZIP OR POSTAL CODE"])
        base = self.median_by_zip.get(zip_code, self.global_median) or self.global_median
        sqft = float(feats_df.iloc[0]["SQUARE FEET"]); beds = float(feats_df.iloc[0]["BEDS"]); baths = float(feats_df.iloc[0]["BATHS"])

        factor = 1.0
        if sqft > 0:
            factor *= min(1.3, max(0.7, (sqft / 1600.0) ** 0.15))
        factor *= (1 + 0.02 * max(0, beds - 3))
        factor *= (1 + 0.015 * max(0, baths - 2))
        return float(base * factor)

    def predict_time_category(self, feats_df: pd.DataFrame, price_value: float) -> int:
        if self.has_time:
            feats_df = feats_df.copy()
            feats_df.loc[:, "PRICE"] = price_value
            X = self._align(feats_df, self.time_cols)
            if self.scaler_time is not None:
                try:
                    X = self.scaler_time.transform(X)
                except Exception:
                    pass
            return int(self.time_model.predict(X)[0])

        zip_code = int(feats_df.iloc[0]["ZIP OR POSTAL CODE"])
        med = self.median_by_zip.get(zip_code, self.global_median) or self.global_median
        ratio = (price_value / med) if med else 1.0
        if ratio <= 0.95: return 0     
        if ratio <= 1.10: return 1     
        return 2                     

    @staticmethod
    def time_label(cat: int) -> str:
        return ("<=30 dias" if cat == 0 else "31-60 dias" if cat == 1 else ">60 dias")
