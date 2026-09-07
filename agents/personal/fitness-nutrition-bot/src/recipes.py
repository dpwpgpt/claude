import json
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Recipe:
    name: str
    category: str
    portion: Optional[str]
    ingredients: Optional[str]
    instructions: Optional[str]


def normalize(text: str) -> str:
    return text.lower().replace("ё", "е")


def load_recipes(path: str) -> List[Recipe]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [
        Recipe(
            name=item["name"],
            category=item["category"],
            portion=item.get("portion"),
            ingredients=item.get("ingredients"),
            instructions=item.get("instructions"),
        )
        for item in raw
    ]


def _term_matches(term: str, haystack: str) -> bool:
    if term in haystack:
        return True
    # Russian words share different endings for case/number, and related nouns
    # and adjectives (e.g. "курица" / "куриное") diverge only near the end -
    # fall back to a shortened stem so common ingredient names still match.
    min_len = 3
    for cut in (1, 2):
        stem = term[: len(term) - cut]
        if len(stem) >= min_len and stem in haystack:
            return True
    return False


CATEGORY_ORDER = ["завтрак", "перекус", "обед", "ужин"]


def recipes_by_category(category: str, recipes: List[Recipe]) -> List[Recipe]:
    return sorted((r for r in recipes if r.category == category), key=lambda r: r.name)


def search_recipes(query: str, recipes: List[Recipe]) -> List[Recipe]:
    terms = [normalize(t) for t in query.replace(",", " ").split() if t.strip()]
    if not terms:
        return []

    results = []
    for recipe in recipes:
        haystack = normalize(f"{recipe.name} {recipe.ingredients or ''}")
        if all(_term_matches(term, haystack) for term in terms):
            results.append(recipe)
    return results


def format_recipe(recipe: Recipe) -> str:
    lines = [recipe.name]
    if recipe.portion:
        lines.append(recipe.portion)
    lines.append("")
    if recipe.ingredients:
        lines.append(f"Ингредиенты: {recipe.ingredients}")
    if recipe.instructions:
        lines.append("")
        lines.append(f"Приготовление: {recipe.instructions}")
    return "\n".join(lines)
