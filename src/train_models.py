import os
import json
import pickle
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.metrics import mean_absolute_error, accuracy_score
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestRegressor

DATA_PATH = "data/sold_data.csv"
OUT_DIR = "models"

DROP_MODEL1 = [
    "ADDRESS", "PRICE", "ORIGINAL LISTING PRICE", "$/SQUARE FOOT",
    "LONGITUDE", "DAYS ON MARKET", "SOLD MONTH", "HOA/MONTH", "ZIP MONTH COUNT"
]


def safe_drop(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    keep = [c for c in df.columns if c not in cols]
    return df[keep]


def ensure_cols(df: pd.DataFrame, cols: list[str]):
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df


def month_from_date(series):
    series = pd.to_datetime(series, errors="coerce")
    return series.dt.month


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_cols(df, [
        "ADDRESS", "PRICE", "SQUARE FEET", "BEDS", "BATHS",
        "LOT SIZE", "YEAR BUILT", "HOA/MONTH", "ZIP OR POSTAL CODE",
        "PROPERTY TYPE", "DAYS ON MARKET", "SOLD DATE", "LISTING DATE",
        "LONGITUDE"
    ])

    num_cols = [
        "PRICE", "SQUARE FEET", "BEDS", "BATHS", "LOT SIZE", "YEAR BUILT",
        "HOA/MONTH", "ZIP OR POSTAL CODE", "DAYS ON MARKET"
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["BED BATH RATIO"] = df["BEDS"] / df["BATHS"].replace(0, 1)
    df["$/SQUARE FOOT"] = df["PRICE"] / df["SQUARE FEET"].replace(0, 1)
    df["SOLD MONTH"] = month_from_date(df["SOLD DATE"]).fillna(month_from_date(df["LISTING DATE"]))

    zip_month = df[["ZIP OR POSTAL CODE", "SOLD MONTH"]].copy()
    zip_month["ZIP MONTH COUNT"] = zip_month.groupby([
        "ZIP OR POSTAL CODE", "SOLD MONTH"
    ])[
        "SOLD MONTH"
    ].transform("count")
    df["ZIP MONTH COUNT"] = zip_month["ZIP MONTH COUNT"].fillna(0)

    df_ohe = pd.get_dummies(df, columns=["PROPERTY TYPE"], prefix=["property_type"])
    return df_ohe


def train_price_model(df_features: pd.DataFrame):
    y = df_features["PRICE"].astype(float)
    X = safe_drop(df_features, DROP_MODEL1)
    X = X.select_dtypes(include=["number"]).copy()

    mask = ~X.isna().any(axis=1)
    X = X[mask]
    y = y[mask]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=0
    )
    feature_cols = X_train.columns.tolist()

    param_grid = {
        "n_estimators": [200, 350],
        "max_depth": [5, 8],
        "min_samples_split": [2, 5],
    }

    gs = GridSearchCV(
        RandomForestRegressor(random_state=0, n_jobs=-1),
        param_grid,
        cv=3,
        scoring="neg_mean_absolute_error",
    )
    gs.fit(X_train, y_train)
    model = gs.best_estimator_

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    cv_scores = -cross_val_score(model, X_train, y_train, cv=5, scoring="neg_mean_absolute_error")
    print("[train_models] PRICE model - best params:", gs.best_params_)
    print(f"   MAE test: {mae:,.0f}")
    print(f"   CV MAE (min): {cv_scores.min():,.0f}")

    return model, feature_cols


def train_time_model(df_features: pd.DataFrame):
    dom = pd.to_numeric(df_features["DAYS ON MARKET"], errors="coerce")
    fallback = dom.median() if not dom.dropna().empty else 45
    TIME_CAT = pd.cut(
        dom.fillna(fallback),
        bins=[-1, 30, 60, np.inf],
        labels=[0, 1, 2]
    ).astype(int)

    drop_time = ["ADDRESS", "LONGITUDE", "SOLD MONTH", "DAYS ON MARKET"]
    Xt = safe_drop(df_features, drop_time)
    Xt = Xt.select_dtypes(include=["number"]).copy()
    Xt["PRICE"] = pd.to_numeric(Xt["PRICE"], errors="coerce").fillna(Xt["PRICE"].median())

    mask = ~Xt.isna().any(axis=1)
    Xt = Xt[mask]
    y_time = TIME_CAT[mask]

    Xt_train, Xt_test, yt_train, yt_test = train_test_split(
        Xt, y_time, test_size=0.2, random_state=0, stratify=y_time
    )

    scaler = StandardScaler().fit(Xt_train)
    Xt_train_s = scaler.transform(Xt_train)
    Xt_test_s = scaler.transform(Xt_test)

    param_knn = {"n_neighbors": [5, 7, 9], "weights": ["uniform", "distance"]}
    gs_knn = GridSearchCV(KNeighborsClassifier(), param_knn, cv=3, scoring="accuracy")
    gs_knn.fit(Xt_train_s, yt_train)
    model = gs_knn.best_estimator_

    preds = model.predict(Xt_test_s)
    acc = accuracy_score(yt_test, preds)
    print("[train_models] TIME model - best params:", gs_knn.best_params_)
    print(f"   ACC test: {acc:.3f}")

    return scaler, model, Xt.columns.tolist()


def main():
    print(f"[train_models] Loading {DATA_PATH} ...")
    df = pd.read_csv(DATA_PATH)
    df_features = build_features(df)

    price_model, feature_cols_model1 = train_price_model(df_features)
    scaler_time, time_model, feature_cols_model2 = train_time_model(df_features)

    os.makedirs(OUT_DIR, exist_ok=True)

    with open(os.path.join(OUT_DIR, "price_xgb.pkl"), "wb") as f:
        pickle.dump(price_model, f)

    with open(os.path.join(OUT_DIR, "time_knn.pkl"), "wb") as f:
        pickle.dump(time_model, f)

    with open(os.path.join(OUT_DIR, "scaler_time.pkl"), "wb") as f:
        pickle.dump(scaler_time, f)

    with open(os.path.join(OUT_DIR, "feature_cols_model1.json"), "w") as f:
        json.dump(feature_cols_model1, f)

    with open(os.path.join(OUT_DIR, "feature_cols_model2.json"), "w") as f:
        json.dump(feature_cols_model2, f)

    print(f"[train_models] saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
