import requests
import pandas as pd
from datetime import timedelta, date
import progressbar

# Helper function to iterate dates, thanks stackoverflow
def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def pull_airq(single_date):
    # Format date as string
    date_str = single_date.strftime("%Y-%m-%d")

    # Set parameters based on date
    params = {
        "from_date_time": f"{date_str}T00:00:00",
        "to_date_time": f"{date_str}T23:59:59",
        "station_code": "all",
        "municipality_id": "all",
        "substance": "all",
        "format": "json",
    }

    # Pull via get and take json
    r = requests.get("http://air.gov.ge/api/get_data_1hour/", params=params)
    js = r.json()

    # Flatten json
    df = pd.io.json.json_normalize(
        js,
        ["stationequipment_set", "data1hour_set"],
        meta=[
            "code",
            "settlement_en",
            "lat",
            "long",
            "elev",
            "address",
            "address_en",
            ["stationequipment_set", "substance", "name"],
        ],
    )

    return df


def pull_airq_range(start_date: date, end_date: date):

    # Iterate through days and pull each day to a list
    out = []

    # Number of days for the progressbar
    date_len = len(list(daterange(start_date, end_date)))

    print(f"Extracting data from air.gov.ge for {start_date} - {end_date}")
    with progressbar.ProgressBar(max_value=date_len) as bar:

        # Iterate through the date range and pull individual records
        for n, single_date in enumerate(daterange(start_date, end_date)):
            out.append(pull_airq(single_date))
            bar.update(n)

    # Concatenate to final
    df = pd.concat(out, sort=False)

    # date_time as datetime
    df["date_time"] = pd.to_datetime(df["date_time"])

    # Swapping cols and renaming that an iritating one
    df = df[df.columns[1:].to_list() + [df.columns[0]]]
    cols = df.columns.to_list()
    cols[-2] = "substance"
    df.columns = cols

    # Also renaming date for fbprophet
    df = df.rename(columns={"date_time": "ds"})
    print("Done.")
    return df


def pull_weather(start_date: date, end_date: date):
    print(f"Extracting data from power.larc.nasa.gov {start_date} - {end_date}")

    """ Request parameters, key thing is the 'parameters' field, which gives us
        our weather variables, and the start and end dates """

    params = {
        "request": "execute",
        "identifier": "SinglePoint",
        "parameters": "WS10M,T2M,PRECTOT,PS",
        "startDate": start_date.strftime("%Y%m%d"),
        "endDate": end_date.strftime("%Y%m%d"),
        "userCommunity": "SSE",
        "tempAverage": "DAILY",
        "outputList": "JSON",
        "lat": "41.7127",
        "lon": "44.8067",
    }

    base_url = "https://power.larc.nasa.gov/cgi-bin/v1/DataAccess.py?"

    # Call api and flatten json with some fugly code
    r = requests.get(base_url, params=params)
    weather = (
        pd.io.json.json_normalize(
            r.json()["features"][0]["properties"]["parameter"]
        )
        .T.reset_index()
        .rename(columns={0: "value"})
    )

    """ Parse into a format that's compatible with the other data, extracting
        date time and variable names from the index and moving long to wide """

    weather = (
        weather["index"]
        .str.split(".")
        .apply(pd.Series)
        .merge(weather["value"], left_index=True, right_index=True)
        .rename(columns={0: "variable", 1: "ds"})
        .assign(ds=lambda x: pd.to_datetime(x["ds"]))
        .pivot(index="ds", columns="variable", values="value")
        .reset_index()
    )

    # A little more housekeeping to make variables readable and drop nulls
    weather = weather[["ds", "WS10M", "PRECTOT", "T2M", "PS"]]
    weather.columns = ["ds", "wind", "precipitation", "temp", "pressure"]
    weather = weather[weather.precipitation != -999]
    print("Done.")
    return weather
