import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes, ConversationHandler

from .claude_service import ClaudeService
from .nutrition import compute_targets
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


def _storage(context: ContextTypes.DEFAULT_TYPE) -> Storage:
    return context.bot_data["storage"]


def _claude(context: ContextTypes.DEFAULT_TYPE) -> ClaudeService:
    return context.bot_data["claude"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я твой личный помощник по питанию и фитнесу.\n\n"
        "Что я умею:\n"
        "• /profile — настроить профиль и рассчитать норму КБЖУ\n"
        "• прислать фото меню — оценю калорийность блюд\n"
        "• написать состав блюда текстом — посчитаю КБЖУ\n"
        "• /plan — составить рацион на день под твою цель\n"
        "• /today — показать итоги за сегодня\n\n"
        "Начни с /profile, чтобы я знал твою норму."
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
        "Теперь можешь:\n"
        "• прислать фото меню — оценю КБЖУ блюд\n"
        "• написать состав блюда текстом — посчитаю калории\n"
        "• использовать /plan — составлю рацион на день\n"
        "• использовать /today — покажу итоги за сегодня",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def profile_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Настройка профиля отменена.", reply_markup=ReplyKeyboardRemove()
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

    await update.message.reply_text("Составляю рацион на день, это может занять немного времени...")

    preferences = " ".join(context.args) if context.args else ""
    try:
        result = _claude(context).generate_diet_plan(
            profile.target_calories, profile.target_protein_g,
            profile.target_fat_g, profile.target_carbs_g,
            profile.goal, preferences,
        )
    except Exception:
        logger.exception("Failed to generate diet plan")
        await update.message.reply_text("Не получилось составить рацион, попробуй ещё раз чуть позже.")
        return

    lines = [result.summary, ""]
    for item in result.meals:
        lines.append(
            f"{item.meal}: {item.dish} — {item.calories:.0f} ккал "
            f"(Б{item.protein_g:.0f}/Ж{item.fat_g:.0f}/У{item.carbs_g:.0f})"
        )
    lines.append("")
    lines.append(
        f"Итого: {result.total_calories:.0f} ккал "
        f"(Б{result.total_protein_g:.0f}/Ж{result.total_fat_g:.0f}/У{result.total_carbs_g:.0f})"
    )
    lines.append("")
    lines.append(result.recommendations)

    await update.message.reply_text("\n".join(lines))


# --- Итоги за день ---


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    storage = _storage(context)
    user_id = update.effective_user.id
    profile = storage.get_profile(user_id)
    entries = storage.today_entries(user_id)

    if not entries:
        await update.message.reply_text(
            "Сегодня ты ещё ничего не записал(а). Пришли фото меню или опиши приём пищи текстом."
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


# --- Фото меню ---


async def handle_menu_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = bytes(await file.download_as_bytearray())

    await update.message.reply_text("Разбираю меню...")

    try:
        analysis = _claude(context).analyze_menu_photo(image_bytes)
    except Exception:
        logger.exception("Failed to analyze menu photo")
        await update.message.reply_text("Не получилось распознать меню, попробуй прислать фото почётче.")
        return

    if not analysis.items:
        await update.message.reply_text("Не нашёл блюд на фото. Попробуй прислать другое фото.")
        return

    context.user_data["pending_menu"] = analysis.items

    lines = ["Вот что удалось разобрать:\n"]
    keyboard = []
    for idx, item in enumerate(analysis.items):
        lines.append(
            f"{idx + 1}. {item.name} ({item.portion}) — {item.calories:.0f} ккал "
            f"(Б{item.protein_g:.0f}/Ж{item.fat_g:.0f}/У{item.carbs_g:.0f}, {item.confidence})"
        )
        keyboard.append(
            [InlineKeyboardButton(f"Записать {idx + 1}", callback_data=f"log_menu:{idx}")]
        )

    if analysis.notes:
        lines.append(f"\n{analysis.notes}")

    await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))


# --- Текстовое описание блюда ---


async def handle_text_meal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    description = update.message.text.strip()
    if not description:
        return

    await update.message.reply_text("Считаю КБЖУ...")

    try:
        estimate = _claude(context).estimate_dish(description)
    except Exception:
        logger.exception("Failed to estimate dish")
        await update.message.reply_text("Не получилось посчитать КБЖУ, попробуй описать состав подробнее.")
        return

    context.user_data["pending_dish"] = estimate

    lines = [f"{estimate.dish_name}:\n"]
    for ing in estimate.ingredients:
        lines.append(f"• {ing.name} ({ing.amount}) — {ing.calories:.0f} ккал")
    lines.append("")
    lines.append(
        f"Итого: {estimate.total_calories:.0f} ккал "
        f"(Б{estimate.total_protein_g:.0f}/Ж{estimate.total_fat_g:.0f}/У{estimate.total_carbs_g:.0f})"
    )

    keyboard = [[InlineKeyboardButton("Записать в дневник", callback_data="log_dish")]]
    await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))


# --- Запись в дневник по кнопке ---


async def handle_log_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    storage = _storage(context)
    user_id = update.effective_user.id

    if query.data.startswith("log_menu:"):
        idx = int(query.data.split(":", 1)[1])
        items = context.user_data.get("pending_menu")
        if not items or idx >= len(items):
            await query.message.reply_text("Это меню уже устарело, пришли фото ещё раз.")
            return
        item = items[idx]
        storage.add_log_entry(
            user_id,
            LogEntry(
                label=item.name, calories=item.calories,
                protein_g=item.protein_g, fat_g=item.fat_g, carbs_g=item.carbs_g,
            ),
        )
        await query.message.reply_text(f"Записал: {item.name} — {item.calories:.0f} ккал")

    elif query.data == "log_dish":
        estimate = context.user_data.get("pending_dish")
        if not estimate:
            await query.message.reply_text("Не нашёл это блюдо, опиши его ещё раз.")
            return
        storage.add_log_entry(
            user_id,
            LogEntry(
                label=estimate.dish_name, calories=estimate.total_calories,
                protein_g=estimate.total_protein_g, fat_g=estimate.total_fat_g,
                carbs_g=estimate.total_carbs_g,
            ),
        )
        await query.message.reply_text(
            f"Записал: {estimate.dish_name} — {estimate.total_calories:.0f} ккал"
        )
