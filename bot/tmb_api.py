import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


def obtener_llegadas(codi_parada):
    TZ = ZoneInfo("Europe/Madrid")
    app_id = os.getenv("TMB_APP_ID")
    app_key = os.getenv("TMB_APP_KEY")
    url_base = f"https://api.tmb.cat/v1/itransit/bus/parades/{codi_parada}"
    query = {
        "app_id": app_id,
        "app_key": app_key,
    }

    r = requests.get(url_base, params=query)
    status = r.status_code
    if status == 200:
        data = r.json()
        linies_trajectes = data["parades"][0]["linies_trajectes"]
        resultat = []
        for i in linies_trajectes:
            nom_linia = i["nom_linia"]
            propers_busos = i["propers_busos"]
            futures_arribades = []
            for k in propers_busos:
                temps_arribada = k["temps_arribada"] / 1000
                dt_object = datetime.fromtimestamp(temps_arribada, TZ)
                futures_arribades.append(dt_object)
            resultat.append({"linia": nom_linia, "horas": futures_arribades})
        return resultat
    else:
        raise Exception(f"Algo no está funcionando (status {status})")


if __name__ == "__main__":
    llegadas = obtener_llegadas("1669")
    print(llegadas[0]["horas"][0].strftime("%H:%M"))
