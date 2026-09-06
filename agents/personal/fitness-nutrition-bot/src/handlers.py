import logging
from typing import List

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes, ConversationHandler

from .composition import MatchedItem, compute_composition
from .food_db import FoodItem
from .nutrition import compute_targets
from .plan_templates import MealTemplate, build_plan, pick_template
from .recipes import Recipe, format_recipe, search_recipes
from .storage import LogEntry, Profile, Storage

logger = logging.getLogger(__name__)

SEX, AGE, HEIGHT, WEIGHT, ACTIVITY, GOAL = range(6)

SEX_OPTIONS = {"Мужской": "male", "Женский": "female"}

ACTIVITY_OPTIONS = {
    "Сидячий образ жизни": "sedentary",
    "Лёгкая активность (1-3 тренировки/нед)": "light",
    "Средняя активность (3-5 тренировок/нед)": "moderate",
    "Высокая активность (6-7 тренировок/нед)": "active",
    "Очень высокая активность (спорт + физ. работа)": "very_active",
}

GOAL_OPTIONS = {
    "Снижение веса": "lose",
    "Поддержание веса": "maintain",
    "Набор массы": "gain",
}

BTN_RECIPE = "🔍 Найти рецепт"
BTN_CALCULATE = "🧮 Рассчитать КБЖУ"
BTN_LOG = "📝 Записать приём пищи"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [[BTN_RECIPE], [BTN_CALCULATE, BTN_LOG]], resize_keyboard=True
)


def _storage(context: ContextTypes.DEFAULT_TYPE) -> Storage:
    return context.bot_data["storage"]


def _foods(context: ContextTypes.DEFAULT_TYPE) -> List[FoodItem]:
    return context.bot_data["foods"]


def _templates(context: ContextTypes.DEFAULT_TYPE) -> List[MealTemplate]:
    return context.bot_data["templates"]


def _recipes(context: ContextTypes.DEFAULT_TYPE) -> List[Recipe]:
    return context.bot_data["recipes"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я твой личный помощник по питанию и фитнесу.\n\n"
        "Кнопки внизу:\n"
        f"• {BTN_RECIPE} — найти рецепт из меню по продуктам\n"
        f"• {BTN_CALCULATE} — посчитать калории по составу\n"
        f"• {BTN_LOG} — посчитать и записать в дневник\n\n"
        "Команды:\n"
        "• /profile — настроить профиль и рассчитать норму КБЖУ\n"
        "• /plan — составить рацион на день под твою цель (можно с уточнением:\n"
        "  /plan вег или /plan низкоуглеводный)\n"
        "• /today — показать итоги за сегодня\n\n"
        "Начни с /profile, чтобы я знал твою норму.",
        reply_markup=MAIN_KEYBOARD,
    )


# --- Кнопки главного меню ---


async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text

    if text == BTN_RECIPE:
        context.user_data["awaiting"] = "recipe"
        await update.message.reply_text("Какие ингредиенты искать? Например: курица картофель")
    elif text == BTN_CALCULATE:
        context.user_data.pop("awaiting", None)
        await update.message.reply_text(
            "Опиши состав, например: курица 150 г, рис 100 г, огурец"
        )
    elif text == BTN_LOG:
        context.user_data.pop("awaiting", None)
        await update.message.reply_text(
            "Опиши, что съел(а), например: курица 150 г, рис 100 г. "
            "Посчитаю КБЖУ и предложу записать в дневник."
        )


# --- Профиль ---


async def profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [list(SEX_OPTIONS.keys())]
    await update.message.reply_text(
        "Начнём настройку профиля.\n\nУкажи пол:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return SEX


async def profile_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text not in SEX_OPTIONS:
        await update.message.reply_text("Пожалуйста, выбери один из вариантов на клавиатуре.")
        return SEX
    context.user_data["sex"] = SEX_OPTIONS[text]
    await update.message.reply_text("Сколько тебе лет?", reply_markup=ReplyKeyboardRemove())
    return AGE


async def profile_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text.strip())
        if not (10 <= age <= 100):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введи возраст числом, например 28.")
        return AGE
    context.user_data["age"] = age
    await update.message.reply_text("Какой у тебя рост в сантиметрах?")
    return HEIGHT


async def profile_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        height = float(update.message.text.strip().replace(",", "."))
        if not (100 <= height <= 250):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введи рост числом в см, например 175.")
        return HEIGHT
    context.user_data["height_cm"] = height
    await update.message.reply_text("Какой у тебя вес в килограммах?")
    return WEIGHT


async def profile_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        weight = float(update.message.text.strip().replace(",", "."))
        if not (30 <= weight <= 300):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введи вес числом в кг, например 70.5.")
        return WEIGHT
    context.user_data["weight_kg"] = weight
    keyboard = [[level] for level in ACTIVITY_OPTIONS]
    await update.message.reply_text(
        "Какой у тебя уровень активности?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ACTIVITY


async def profile_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text not in ACTIVITY_OPTIONS:
        await update.message.reply_text("Выбери вариант на клавиатуре.")
        return ACTIVITY
    context.user_data["activity_level"] = ACTIVITY_OPTIONS[text]
    keyboard = [[g] for g in GOAL_OPTIONS]
    await update.message.reply_text(
        "Какая у тебя цель?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return GOAL


async def profile_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text not in GOAL_OPTIONS:
        await update.message.reply_text("Выбери вариант на клавиатуре.")
        return GOAL
    context.user_data["goal"] = GOAL_OPTIONS[text]

    data = context.user_data
    targets = compute_targets(
        data["sex"], data["weight_kg"], data["height_cm"], data["age"],
        data["activity_level"], data["goal"],
    )

    _storage(context).save_profile(
        Profile(
            user_id=update.effective_user.id,
            sex=data["sex"],
            age=data["age"],
            height_cm=data["height_cm"],
            weight_kg=data["weight_kg"],
            activity_level=data["activity_level"],
            goal=data["goal"],
            target_calories=targets.calories,
            target_protein_g=targets.protein_g,
            target_fat_g=targets.fat_g,
            target_carbs_g=targets.carbs_g,
        )
    )

    await update.message.reply_text(
        "Профиль сохранён!\n\n"
        "Целевая суточная норма:\n"
        f"Калории: {targets.calories:.0f} ккал\n"
        f"Белки: {targets.protein_g:.0f} г\n"
        f"Жиры: {targets.fat_g:.0f} г\n"
        f"Углеводы: {targets.carbs_g:.0f} г\n\n"
        "Теперь можешь пользоваться кнопками внизу или командой /plan, /today.",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def profile_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Настройка профиля отменена.", reply_markup=MAIN_KEYBOARD
    )
    return ConversationHandler.END


# --- Рацион на день ---


async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    profile = _storage(context).get_profile(update.effective_user.id)
    if not profile:
        await update.message.reply_text(
            "Сначала настрой профиль командой /profile — так я буду знать твою норму КБЖУ."
        )
        return

    foods = _foods(context)
    templates = _templates(context)

    target_protein_pct = profile.target_protein_g * 4 / profile.target_calories
    target_fat_pct = profile.target_fat_g * 9 / profile.target_calories
    target_carbs_pct = profile.target_carbs_g * 4 / profile.target_calories

    keyword = " ".join(context.args) if context.args else None
    template = pick_template(templates, foods, target_protein_pct, target_fat_pct, target_carbs_pct, keyword)
    result = build_plan(template, foods, profile.target_calories)

    lines = [f"Рацион «{result.template_name}» на {profile.target_calories:.0f} ккал:\n"]
    current_meal = None
    for line in result.lines:
        if line.meal != current_meal:
            current_meal = line.meal
            lines.append(f"\n{current_meal}:")
        lines.append(f"• {line.food_name} — {line.grams:.0f} г ({line.calories:.0f} ккал)")

    lines.append("")
    lines.append(
        f"Итого: {result.total_calories:.0f} ккал "
        f"(Б{result.total_protein:.0f}/Ж{result.total_fat:.0f}/У{result.total_carbs:.0f})"
    )
    lines.append(
        "\nЭто приблизительный рацион по шаблону, реальные пропорции БЖУ могут "
        "немного отличаться от целевых. Другой шаблон: /plan вег или /plan низкоуглеводный."
    )

    await update.message.reply_text("\n".join(lines))


# --- Итоги за день ---


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    storage = _storage(context)
    user_id = update.effective_user.id
    profile = storage.get_profile(user_id)
    entries = storage.today_entries(user_id)

    if not entries:
        await update.message.reply_text(
            "Сегодня ты ещё ничего не записал(а). Опиши приём пищи текстом, например: "
            "курица 150 г, рис 100 г."
        )
        return

    total_cal = sum(e.calories for e in entries)
    total_protein = sum(e.protein_g for e in entries)
    total_fat = sum(e.fat_g for e in entries)
    total_carbs = sum(e.carbs_g for e in entries)

    lines = ["Записи за сегодня:"]
    for e in entries:
        lines.append(f"• {e.label} — {e.calories:.0f} ккал")
    lines.append("")
    lines.append(
        f"Итого: {total_cal:.0f} ккал, Б {total_protein:.0f} г / "
        f"Ж {total_fat:.0f} г / У {total_carbs:.0f} г"
    )

    if profile:
        lines.append("")
        lines.append(
            f"Цель на день: {profile.target_calories:.0f} ккал "
            f"(Б {profile.target_protein_g:.0f} / Ж {profile.target_fat_g:.0f} / "
            f"У {profile.target_carbs_g:.0f})"
        )
        lines.append(f"Осталось: {profile.target_calories - total_cal:.0f} ккал")

    await update.message.reply_text("\n".join(lines))


# --- Текстовое описание приёма пищи ---


async def handle_text_meal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    description = update.message.text.strip()
    if not description:
        return

    if context.user_data.pop("awaiting", None) == "recipe":
        await _run_recipe_search(update, context, description)
        return

    matches = compute_composition(description, _foods(context))
    if not matches:
        await update.message.reply_text(
            "Не понял состав. Опиши в формате: курица 150 г, рис 100 г, огурец."
        )
        return

    matched = [m for m in matches if m.food is not None]
    unmatched = [m for m in matches if m.food is None]

    lines = []
    for m in matched:
        lines.append(f"• {m.food.name} — {m.grams:.0f} г — {m.calories:.0f} ккал")

    if unmatched:
        names = ", ".join(m.query for m in unmatched)
        lines.append(f"\nНе нашёл в базе: {names}. Попробуй переформулировать название.")

    if not matched:
        await update.message.reply_text("\n".join(lines))
        return

    total_calories = sum(m.calories for m in matched)
    total_protein = sum(m.protein for m in matched)
    total_fat = sum(m.fat for m in matched)
    total_carbs = sum(m.carbs for m in matched)

    lines.append("")
    lines.append(
        f"Итого: {total_calories:.0f} ккал (Б{total_protein:.0f}/Ж{total_fat:.0f}/У{total_carbs:.0f})"
    )

    context.user_data["pending_composition"] = matched

    keyboard = [[InlineKeyboardButton("Записать в дневник", callback_data="log_composition")]]
    await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Распознавание фото не поддерживается. Опиши состав приёма пищи текстом, "
        "например: курица 150 г, рис 100 г, огурец."
    )


# --- Поиск рецептов по ингредиентам ---


async def _run_recipe_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    results = search_recipes(query, _recipes(context))

    if not results:
        await update.message.reply_text(
            "Рецептов с такими ингредиентами в меню не нашлось. Попробуй другой запрос "
            "или меньше ингредиентов сразу."
        )
        return

    if len(results) == 1:
        await update.message.reply_text(format_recipe(results[0]))
        return

    context.user_data["recipe_results"] = results

    keyboard = [
        [InlineKeyboardButton(r.name, callback_data=f"recipe:{idx}")]
        for idx, r in enumerate(results[:20])
    ]
    await update.message.reply_text(
        f"Нашёл {len(results)} рецепт(ов), выбери:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def recipe_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Напиши после команды ингредиенты, например:\n/recipe курица картофель"
        )
        return

    await _run_recipe_search(update, context, " ".join(context.args))


# --- Запись в дневник / выбор рецепта по кнопке ---


async def handle_log_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data.startswith("recipe:"):
        idx = int(query.data.split(":", 1)[1])
        results: List[Recipe] = context.user_data.get("recipe_results")
        if not results or idx >= len(results):
            await query.message.reply_text("Список рецептов устарел, поищи ещё раз.")
            return
        await query.message.reply_text(format_recipe(results[idx]))
        return

    if query.data != "log_composition":
        return

    matched: List[MatchedItem] = context.user_data.get("pending_composition")
    if not matched:
        await query.message.reply_text("Не нашёл этот приём пищи, опиши его ещё раз.")
        return

    label = ", ".join(m.food.name for m in matched)
    total_calories = sum(m.calories for m in matched)
    total_protein = sum(m.protein for m in matched)
    total_fat = sum(m.fat for m in matched)
    total_carbs = sum(m.carbs for m in matched)

    _storage(context).add_log_entry(
        update.effective_user.id,
        LogEntry(
            label=label, calories=total_calories,
            protein_g=total_protein, fat_g=total_fat, carbs_g=total_carbs,
        ),
    )
    await query.message.reply_text(f"Записал: {label} — {total_calories:.0f} ккал")
