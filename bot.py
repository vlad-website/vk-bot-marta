import os
import requests
from flask import Flask, request
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Токены
VK_TOKEN = os.getenv("VK_TOKEN")
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# VK API
vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()

# Состояния пользователей
users = {}

# ------------------- Клавиатуры -------------------
def get_choice_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Уютное", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Свежее", color=VkKeyboardColor.POSITIVE)
    return keyboard.get_keyboard()

def get_feel_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Теплое ощущение", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Свежее ощущение", color=VkKeyboardColor.POSITIVE)
    return keyboard.get_keyboard()

def get_smell_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Сладкий", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Древесный", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Цветочный", color=VkKeyboardColor.POSITIVE)
    return keyboard.get_keyboard()

def get_final_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Да, давайте", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("Попробовать другие ароматы", color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()

# ------------------- Telegram уведомления -------------------
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = {"chat_id": TG_CHAT_ID, "text": message}
    requests.post(url, data=data)

# ------------------- Основная логика бота -------------------
def handle_message(user_id, text, original_text):
    text_lower = text.lower()

    # Создаём запись пользователя, если её нет
    if user_id not in users:
        users[user_id] = {"state": None, "started": False}

    # Приветствие при первом сообщении
    if not users[user_id]["started"]:
        users[user_id]["started"] = True
        vk.messages.send(
            user_id=user_id,
            message=(
                "Привет, я помощник MN98 🙌🏻\n\n"
                "Если хочешь сделать индивидуальную свечу и выбрать уникальный аромат, напиши слово Memory ✨\n\n"
                "Или напиши любой интересующий тебя вопрос 😊"
            ),
            random_id=0
        )
        return

    state = users[user_id]["state"]

    # Режим сна
    if state == "sleep":
        if "memory" in text_lower:
            users[user_id]["state"] = None
        else:
            return

    # 1. Старт
    if "memory" in text_lower or "мемори" in text_lower:
        users[user_id]["state"] = "waiting_memory_text"
        first_name = vk.users.get(user_ids=user_id)[0]["first_name"]
        vk.messages.send(
            user_id=user_id,
            message=(
                f"Хорошо, {first_name}!\n"
                "Давай попробуем найти твой Memory Number\n"
                "Я задам пару простых вопросов:\n\n"
                "Скажи, какой момент или ощущение тебе сейчас ближе всего?\n"
                "(Это может быть что угодно — место, время, чувство)"
            ),
            random_id=0
        )
        return

    # 2. Пользователь отправил воспоминание
    if state == "waiting_memory_text":
        users[user_id]["memory"] = original_text
        users[user_id]["state"] = "waiting_feel"
        vk.messages.send(
            user_id=user_id,
            message="Отлично! Скажи пожалуйста, как ты ощущаешь: это что-то теплое, или свежее?",
            keyboard=get_feel_keyboard(),
            random_id=0
        )
        return

    if state == "waiting_feel":
        if text_lower in ["теплое ощущение", "свежее ощущение"]:
            users[user_id]["feel"] = text_lower
            users[user_id]["state"] = "waiting_smell"
            vk.messages.send(
                user_id=user_id,
                message="А если представить этот момент как запах — он скорее сладкий, древесный или цветочный?",
                keyboard=get_smell_keyboard(),
                random_id=0
            )
        else:
            vk.messages.send(
                user_id=user_id,
                message="Не понимаю 😅 Выбери вариант на кнопках ниже:",
                keyboard=get_feel_keyboard(),
                random_id=0
            )
        return

    if state == "waiting_smell":
        if text_lower not in ["сладкий", "древесный", "цветочный"]:
            vk.messages.send(
                user_id=user_id,
                message="Не понимаю 😅 Выбери вариант на кнопках ниже:",
                keyboard=get_smell_keyboard(),
                random_id=0
            )
            return

        users[user_id]["smell"] = text_lower
        feel = users[user_id]["feel"]
        smell = text_lower

        # Подбор результата
        if feel == "теплое ощущение" and smell == "сладкий":
            result = "Какао, Черничный чизкейк"
        elif feel == "свежее ощущение" and smell == "сладкий":
            result = "Кленовый сироп и корица"
        elif feel == "теплое ощущение" and smell == "древесный":
            result = "Еловые шишки и хвоя"
        elif feel == "свежее ощущение" and smell == "древесный":
            result = "Американская пихта"
        elif feel == "теплое ощущение" and smell == "цветочный":
            result = "Кашемировое дерево"
        elif feel == "свежее ощущение" and smell == "цветочный":
            result = "Вербена"
        else:
            result = "Что-то особенное 🙂"

        users[user_id]["state"] = "final_choice"
        vk.messages.send(
            user_id=user_id,
            message=(
                f"Великолепный выбор 🙌🏻\n\n"
                f"Могу предложить: {result}\n\n"
                "Я думаю, это идеально попадает в твой запрос ✨\n\n"
                "Могу оформить для тебя прямо сейчас"
            ),
            keyboard=get_final_keyboard(),
            random_id=0
        )
        return

    if state == "final_choice":
        if text_lower == "да, давайте":
            vk.messages.send(
                user_id=user_id,
                message=(
                    "Отлично! Сейчас с вами свяжется менеджер 😊\n\n"
                    "Если захочешь подобрать другой аромат — напиши memory ✨"
                ),
                random_id=0
            )
            send_telegram(
                f"Новый клиент!\n"
                f"ID: {user_id}\n"
                f"Воспоминание: {users[user_id].get('memory')}\n"
                f"Ощущение: {users[user_id].get('feel')}\n"
                f"Аромат: {users[user_id].get('smell')}\n"
                f"Предложено: {result}"
            )
            users[user_id]["state"] = "sleep"
        elif text_lower == "попробовать другие ароматы":
            users[user_id]["state"] = "waiting_memory_text"
            vk.messages.send(
                user_id=user_id,
                message="Давай попробуем заново 😊 Напиши своё ощущение:",
                random_id=0
            )
        else:
            vk.messages.send(
                user_id=user_id,
                message="Пожалуйста, выбери вариант на кнопках 😊",
                keyboard=get_final_keyboard(),
                random_id=0
            )
        return

    # Если пользователь написал вне сценария
    if state is None:
        first_name = vk.users.get(user_ids=user_id)[0]["first_name"]
        send_telegram(
            f"⚠️ Клиент написал вне сценария\n\n"
            f"Имя: {first_name}\n"
            f"ID: {user_id}\n"
            f"Сообщение: {original_text}"
        )
        users[user_id]["state"] = "sleep"

# ------------------- Flask Webhook -------------------
@app.route("/", methods=["POST"])
def webhook():
    data = request.json

    # Для подтверждения сервиса VK при setup
    if "type" in data and data["type"] == "confirmation":
        return os.getenv("VK_CONFIRMATION_CODE")  # VK выдаст этот код

    # Основные события
    if "type" in data and data["type"] == "message_new":
        obj = data["object"]
        user_id = obj["from_id"]
        text = obj["text"]
        handle_message(user_id, text, obj["text"])
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)