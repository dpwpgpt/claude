import difflib
import json
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FoodItem:
    name: str
    aliases: List[str]
    calories: float
    protein: float
    fat: float
    carbs: float
    default_grams: Optional[float] = None


def normalize(text: str) -> str:
    return text.strip().lower().replace("ё", "е")


def load_foods(path: str) -> List[FoodItem]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [
        FoodItem(
            name=item["name"],
            aliases=item.get("aliases", []),
            calories=item["calories"],
            protein=item["protein"],
            fat=item["fat"],
            carbs=item["carbs"],
            default_grams=item.get("default_grams"),
        )
        for item in raw
    ]


def find_food(query: str, foods: List[FoodItem]) -> Optional[FoodItem]:
    query_norm = normalize(query)
    if not query_norm:
        return None

    lookup = {}
    for food in foods:
        for label in [food.name, *food.aliases]:
            lookup[normalize(label)] = food

    if query_norm in lookup:
        return lookup[query_norm]

    matches = difflib.get_close_matches(query_norm, lookup.keys(), n=1, cutoff=0.6)
    if matches:
        return lookup[matches[0]]
    return None


def get_food_by_name(name: str, foods: List[FoodItem]) -> Optional[FoodItem]:
    for food in foods:
        if food.name == name:
            return food
    return None
