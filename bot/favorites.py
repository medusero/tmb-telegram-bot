import json
import os
from json.decoder import JSONDecodeError

ugly_path = os.path.join(os.path.dirname(__file__), "..", "data", "favorites.json")
clean_path = os.path.abspath(ugly_path)


def cargar_favoritos():
    if os.path.isfile(clean_path):
        try:
            with open(clean_path, "r") as file:
                favorites = json.load(file)
                return favorites
        except JSONDecodeError:
            return {}
    else:
        favorites = {}
        return favorites


def guardar_favoritos(f):
    with open(clean_path, "w") as file:
        json.dump(f, file)


def listar_favoritos():
    favorites = cargar_favoritos()
    lines = [f"- {key}: {value}" for key, value in favorites.items()]
    markdown_list = "\n".join(lines)
    return markdown_list


def borrar_favoritos(f):
    favoritos = cargar_favoritos()
    borrado = favoritos.pop(f)
    guardar_favoritos(favoritos)
    return borrado
