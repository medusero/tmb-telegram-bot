import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


def get_arrivals(stop_code):
    TZ = ZoneInfo("Europe/Madrid")
    app_id = os.getenv("TMB_APP_ID")
    app_key = os.getenv("TMB_APP_KEY")
    base_url = f"https://api.tmb.cat/v1/itransit/bus/parades/{stop_code}"
    query = {
        "app_id": app_id,
        "app_key": app_key,
    }

    r = requests.get(base_url, params=query, timeout=10)
    status = r.status_code
    if status == 200:
        data = r.json()
        line_routes = data["parades"][0]["linies_trajectes"]
        result = []
        for i in line_routes:
            line_name = i["nom_linia"]
            upcoming_buses = i["propers_busos"]
            arrival_times = []
            for k in upcoming_buses:
                arrival_epoch_seconds = k["temps_arribada"] / 1000
                dt_object = datetime.fromtimestamp(arrival_epoch_seconds, TZ)
                arrival_times.append(dt_object)
            result.append({"line_name": line_name, "arrival_times": arrival_times})
        return result
    else:
        raise Exception(f"Algo no está funcionando (status {status})")


if __name__ == "__main__":
    arrivals = get_arrivals("1669")
    print(arrivals[0]["arrival_times"][0].strftime("%H:%M"))
