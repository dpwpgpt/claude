import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .food_db import FoodItem, find_food

DEFAULT_PORTION_GRAMS = 100.0

_WEIGHT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(г|гр|грамм\w*|кг|мл|ml|g)?\b", re.IGNORECASE
)


@dataclass
class MatchedItem:
    query: str
    grams: float
    food: Optional[FoodItem]
    calories: float
    protein: float
    fat: float
    carbs: float


def parse_composition(text: str) -> List[Tuple[str, float]]:
    segments = re.split(r"[,;\n]+", text)
    items = []
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        match = None
        for match in _WEIGHT_RE.finditer(segment):
            pass  # take the last number found in the segment as the weight

        if match:
            weight = float(match.group(1).replace(",", "."))
            if match.group(2) and match.group(2).lower() == "кг":
                weight *= 1000
            name = (segment[: match.start()] + segment[match.end():]).strip(" -—:.")
        else:
            weight = DEFAULT_PORTION_GRAMS
            name = segment.strip(" -—:.")

        if name:
            items.append((name, weight))

    return items


def compute_composition(text: str, foods: List[FoodItem]) -> List[MatchedItem]:
    results = []
    for name, grams in parse_composition(text):
        food = find_food(name, foods)
        if food is None:
            results.append(
                MatchedItem(query=name, grams=grams, food=None, calories=0, protein=0, fat=0, carbs=0)
            )
            continue

        factor = grams / 100.0
        results.append(
            MatchedItem(
                query=name,
                grams=grams,
                food=food,
                calories=food.calories * factor,
                protein=food.protein * factor,
                fat=food.fat * factor,
                carbs=food.carbs * factor,
            )
        )
    return results
