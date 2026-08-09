import json
import os
from json.decoder import JSONDecodeError

ugly_path = os.path.join(os.path.dirname(__file__), "..", "data", "favorites.json")
clean_path = os.path.abspath(ugly_path)


def load_favorites():
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


def save_favorites(f):
    with open(clean_path, "w") as file:
        json.dump(f, file)


def list_favorites():
    favorites = load_favorites()
    lines = [f"- {key}: {value}" for key, value in favorites.items()]
    markdown_list = "\n".join(lines)
    return markdown_list


def delete_favorites(f):
    favorites = load_favorites()
    removed = favorites.pop(f)
    save_favorites(favorites)
    return removed
