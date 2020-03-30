from pull_data import pull_airq_range, pull_weather
from datetime import date, datetime
import pandas as pd
from fbprophet import Prophet
import progressbar


def air_processed(start_date, end_date, cut_points, cut_labs, *args, **kwargs):
    air = (
        pull_airq_range(start_date, end_date)
        .query('settlement_en == "Tbilisi"')
        .groupby(["ds", "substance"])["value"]
        .mean()
        .reset_index()
        .pivot(index="ds", columns="substance", values="value")
        .reset_index()
        .assign(
            cut=lambda x: pd.cut(
                x["ds"], bins=cut_points, labels=cut_labs, include_lowest=True
            )
        )
    )
    return air


def extract_seasonality(air: pd.DataFrame):
    subs = ["PM10", "PM2.5", "NO2", "O3", "SO2", "CO"]
    with progressbar.ProgressBar(max_value=len(subs)) as bar:
        for n, sub in enumerate(subs):
            df = air[["ds", sub]].rename(columns={sub: "y"})
            m = Prophet()
            m.fit(df)
            future = m.make_future_dataframe(periods=1)
            out = m.predict(future)
            out = out[[i for i in out if "_" not in i and i != "yhat"]]
            out["ds"] = pd.to_datetime(out.ds)
            out = out.query("ds < datetime.now()")
            out = out.rename(
                columns={i: f"{sub}_" + i for i in out if i != "ds"}
            )
            air = air.merge(out, on="ds", how="left")
            bar.update(n)
    return air


def load_processed_data(start_date, end_date, *args, **kwargs):
    air = air_processed(start_date, end_date, *args, **kwargs)
    air = extract_seasonality(air)
    air = pd.merge_asof(
        air, pull_weather(start_date, end_date), on="ds"
    ).dropna()
    return air
