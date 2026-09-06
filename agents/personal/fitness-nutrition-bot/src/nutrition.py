from dataclasses import dataclass

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

GOAL_CALORIE_ADJUSTMENT = {
    "lose": -0.15,
    "maintain": 0.0,
    "gain": 0.12,
}

PROTEIN_G_PER_KG = {
    "lose": 2.0,
    "maintain": 1.8,
    "gain": 1.8,
}

FAT_SHARE_OF_CALORIES = 0.27


@dataclass
class Targets:
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float


def bmr_mifflin_st_jeor(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def compute_targets(
    sex: str,
    weight_kg: float,
    height_cm: float,
    age: int,
    activity_level: str,
    goal: str,
) -> Targets:
    bmr = bmr_mifflin_st_jeor(sex, weight_kg, height_cm, age)
    tdee = bmr * ACTIVITY_MULTIPLIERS[activity_level]
    calories = tdee * (1 + GOAL_CALORIE_ADJUSTMENT[goal])

    protein_g = PROTEIN_G_PER_KG[goal] * weight_kg
    fat_g = (calories * FAT_SHARE_OF_CALORIES) / 9
    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    carbs_g = max((calories - protein_kcal - fat_kcal) / 4, 0)

    return Targets(
        calories=round(calories),
        protein_g=round(protein_g),
        fat_g=round(fat_g),
        carbs_g=round(carbs_g),
    )
