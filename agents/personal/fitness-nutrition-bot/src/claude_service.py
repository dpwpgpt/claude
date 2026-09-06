import base64

import anthropic

from . import models

MENU_SYSTEM_PROMPT = (
    "Ты — нутрициолог-ассистент. Тебе показывают фото меню кафе/ресторана. "
    "Определи все блюда, которые удаётся прочитать, и для каждого оцени порцию и КБЖУ "
    "(калории, белки, жиры, углеводы) на основе типичного состава такого блюда и своих знаний "
    "о кулинарии. Если вес порции не указан в меню, оцени его по типичной подаче. "
    "Указывай уверенность оценки (confidence): high — если состав и вес понятны, "
    "medium — если пришлось оценивать по названию, low — если данных очень мало."
)

DISH_SYSTEM_PROMPT = (
    "Ты — нутрициолог-ассистент. Пользователь описывает состав блюда или приёма пищи "
    "(ингредиенты и их количество). Разбей блюдо на ингредиенты, оцени КБЖУ каждого "
    "ингредиента и посчитай итоговую сумму. Используй стандартные справочные значения "
    "КБЖУ на 100 г продукта и пересчитывай на указанное количество."
)

PLAN_SYSTEM_PROMPT = (
    "Ты — нутрициолог-ассистент, который составляет дневной рацион питания под целевые "
    "калории и БЖУ пользователя. Предлагай сбалансированные, реалистичные блюда "
    "(завтрак, обед, ужин и при необходимости 1-2 перекуса), избегай крайностей. "
    "Сумма калорий и БЖУ по всем приёмам пищи должна быть близка к целевым значениям "
    "(отклонение не более 5-10%)."
)


class ClaudeService:
    def __init__(self, client: anthropic.Anthropic, model: str):
        self._client = client
        self._model = model

    def analyze_menu_photo(
        self, image_bytes: bytes, media_type: str = "image/jpeg"
    ) -> models.MenuAnalysis:
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = self._client.messages.parse(
            model=self._model,
            max_tokens=16000,
            system=MENU_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Определи блюда на этом фото меню и оцени их КБЖУ.",
                        },
                    ],
                }
            ],
            output_format=models.MenuAnalysis,
        )
        return response.parsed_output

    def estimate_dish(self, description: str) -> models.DishEstimate:
        response = self._client.messages.parse(
            model=self._model,
            max_tokens=16000,
            system=DISH_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": description}],
            output_format=models.DishEstimate,
        )
        return response.parsed_output

    def generate_diet_plan(
        self,
        target_calories: float,
        target_protein_g: float,
        target_fat_g: float,
        target_carbs_g: float,
        goal: str,
        preferences: str = "",
    ) -> models.DietPlan:
        prompt = (
            "Составь дневной рацион питания.\n"
            f"Цель: {goal}.\n"
            f"Целевые калории: {target_calories:.0f} ккал.\n"
            f"Целевые белки: {target_protein_g:.0f} г, жиры: {target_fat_g:.0f} г, "
            f"углеводы: {target_carbs_g:.0f} г.\n"
        )
        if preferences:
            prompt += f"Пожелания пользователя: {preferences}.\n"

        response = self._client.messages.parse(
            model=self._model,
            max_tokens=16000,
            system=PLAN_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=models.DietPlan,
        )
        return response.parsed_output
