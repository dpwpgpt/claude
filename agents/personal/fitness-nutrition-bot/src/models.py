from typing import List, Optional

from pydantic import BaseModel, Field


class MenuItem(BaseModel):
    name: str = Field(description="Название блюда, как оно указано в меню")
    portion: str = Field(description="Порция/вес, например '250 г' или '1 шт'")
    calories: float = Field(description="Оценка калорийности порции, ккал")
    protein_g: float = Field(description="Белки, г")
    fat_g: float = Field(description="Жиры, г")
    carbs_g: float = Field(description="Углеводы, г")
    confidence: str = Field(description="Уверенность оценки: high, medium или low")


class MenuAnalysis(BaseModel):
    items: List[MenuItem]
    notes: Optional[str] = Field(
        default=None, description="Общие замечания, если фото плохо читается"
    )


class Ingredient(BaseModel):
    name: str
    amount: str
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float


class DishEstimate(BaseModel):
    dish_name: str
    ingredients: List[Ingredient]
    total_calories: float
    total_protein_g: float
    total_fat_g: float
    total_carbs_g: float


class MealPlanItem(BaseModel):
    meal: str
    dish: str
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float


class DietPlan(BaseModel):
    summary: str
    meals: List[MealPlanItem]
    total_calories: float
    total_protein_g: float
    total_fat_g: float
    total_carbs_g: float
    recommendations: str
