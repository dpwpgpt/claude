import json
from dataclasses import dataclass
from typing import Dict, List, Optional

from .food_db import FoodItem, get_food_by_name


@dataclass
class TemplateFoodRef:
    food: str
    grams: float


@dataclass
class MealTemplate:
    name: str
    tags: List[str]
    meals: Dict[str, List[TemplateFoodRef]]


@dataclass
class PlanLine:
    meal: str
    food_name: str
    grams: float
    calories: float
    protein: float
    fat: float
    carbs: float


@dataclass
class PlanResult:
    template_name: str
    lines: List[PlanLine]
    total_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float


def load_templates(path: str) -> List[MealTemplate]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    templates = []
    for entry in raw:
        meals = {
            meal_name: [TemplateFoodRef(food=item["food"], grams=item["grams"]) for item in items]
            for meal_name, items in entry["meals"].items()
        }
        templates.append(MealTemplate(name=entry["name"], tags=entry.get("tags", []), meals=meals))
    return templates


def _template_macros(template: MealTemplate, foods: List[FoodItem]):
    calories = protein = fat = carbs = 0.0
    for items in template.meals.values():
        for ref in items:
            food = get_food_by_name(ref.food, foods)
            if food is None:
                continue
            factor = ref.grams / 100.0
            calories += food.calories * factor
            protein += food.protein * factor
            fat += food.fat * factor
            carbs += food.carbs * factor
    return calories, protein, fat, carbs


def pick_template(
    templates: List[MealTemplate],
    foods: List[FoodItem],
    target_protein_pct: float,
    target_fat_pct: float,
    target_carbs_pct: float,
    keyword: Optional[str] = None,
) -> MealTemplate:
    if keyword:
        keyword_norm = keyword.strip().lower()
        for template in templates:
            if keyword_norm in [t.lower() for t in template.tags] or keyword_norm in template.name.lower():
                return template

    best_template = templates[0]
    best_distance = None
    for template in templates:
        calories, protein, fat, carbs = _template_macros(template, foods)
        if calories == 0:
            continue
        protein_pct = protein * 4 / calories
        fat_pct = fat * 9 / calories
        carbs_pct = carbs * 4 / calories
        distance = (
            (protein_pct - target_protein_pct) ** 2
            + (fat_pct - target_fat_pct) ** 2
            + (carbs_pct - target_carbs_pct) ** 2
        )
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_template = template

    return best_template


def build_plan(template: MealTemplate, foods: List[FoodItem], target_calories: float) -> PlanResult:
    base_calories, _, _, _ = _template_macros(template, foods)
    factor = target_calories / base_calories if base_calories else 1.0

    lines: List[PlanLine] = []
    total_calories = total_protein = total_fat = total_carbs = 0.0

    for meal_name, items in template.meals.items():
        for ref in items:
            food = get_food_by_name(ref.food, foods)
            if food is None:
                continue
            grams = ref.grams * factor
            portion_factor = grams / 100.0
            calories = food.calories * portion_factor
            protein = food.protein * portion_factor
            fat = food.fat * portion_factor
            carbs = food.carbs * portion_factor

            lines.append(
                PlanLine(
                    meal=meal_name, food_name=food.name, grams=grams,
                    calories=calories, protein=protein, fat=fat, carbs=carbs,
                )
            )
            total_calories += calories
            total_protein += protein
            total_fat += fat
            total_carbs += carbs

    return PlanResult(
        template_name=template.name,
        lines=lines,
        total_calories=total_calories,
        total_protein=total_protein,
        total_fat=total_fat,
        total_carbs=total_carbs,
    )
