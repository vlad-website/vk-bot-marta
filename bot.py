import os
import time
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
VK_CONFIRMATION_CODE = os.getenv("VK_CONFIRMATION_CODE")

# VK API
vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()

# Состояния пользователей
users = {}

# Защита от дублей событий
processed_events = set()

# ------------------- Клавиатуры -------------------
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

# ------------------- Telegram -------------------
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": message}
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print("Ошибка Telegram:", e)

# ------------------- Логика -------------------
def handle_message(user_id, text):
    text_lower = text.lower()

    if user_id not in users:
        users[user_id] = {
            "state": None,
            "started": False,
            "last_time": 0
        }

    # анти-спам (важно при пробуждении)
    now = time.time()
    if now - users[user_id]["last_time"] < 1:
        return
    users[user_id]["last_time"] = now

    # игнор "Начать"
    if text_lower == "начать":
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

    # первое сообщение
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

    # режим сна
    if state == "sleep":
        if "memory" in text_lower:
            users[user_id]["state"] = None
        else:
            return

    # старт сценария
    if "memory" in text_lower or "мемори" in text_lower:
        users[user_id]["state"] = "waiting_memory_text"
        first_name = vk.users.get(user_ids=user_id)[0]["first_name"]

        vk.messages.send(
            user_id=user_id,
            message=(
                f"Хорошо, {first_name}! 😊\n"
                "Давай попробуем найти твой Memory Number 🔢✨\n"
                "Я задам пару простых вопросов:\n\n"
                "Скажи, какой момент или ощущение тебе сейчас ближе всего? 🤔💭\n"
                "(Это может быть что угодно — место, время или чувство 🌍🕰️❤️)"
            ),
            random_id=0
        )
        return

    if state == "waiting_memory_text":
        users[user_id]["memory"] = text
        users[user_id]["state"] = "waiting_feel"

        vk.messages.send(
            user_id=user_id,
            message="Это ощущение теплое 🔥 или свежее ❄️?",
            keyboard=get_feel_keyboard(),
            random_id=0
        )
        return

    if state == "waiting_feel":
        if text_lower not in ["теплое ощущение", "свежее ощущение"]:
            vk.messages.send(
                user_id=user_id,
                message="Выбери вариант на кнопках 👇",
                keyboard=get_feel_keyboard(),
                random_id=0
            )
            return

        users[user_id]["feel"] = text_lower
        users[user_id]["state"] = "waiting_smell"

        vk.messages.send(
            user_id=user_id,
            message="Какой это запах? 👃🌸",
            keyboard=get_smell_keyboard(),
            random_id=0
        )
        return

    if state == "waiting_smell":
        if text_lower not in ["сладкий", "древесный", "цветочный"]:
            vk.messages.send(
                user_id=user_id,
                message="Выбери вариант 👇",
                keyboard=get_smell_keyboard(),
                random_id=0
            )
            return

        users[user_id]["smell"] = text_lower
        feel = users[user_id]["feel"]

        # результат
        if feel == "теплое ощущение" and text_lower == "сладкий":
            result = "Какао, Черничный чизкейк"
        elif feel == "свежее ощущение" and text_lower == "сладкий":
            result = "Кленовый сироп и корица"
        elif feel == "теплое ощущение" and text_lower == "древесный":
            result = "Еловые шишки и хвоя"
        elif feel == "свежее ощущение" and text_lower == "древесный":
            result = "Американская пихта"
        elif feel == "теплое ощущение" and text_lower == "цветочный":
            result = "Кашемировое дерево"
        else:
            result = "Вербена"

        users[user_id]["result"] = result
        users[user_id]["state"] = "final_choice"

        vk.messages.send(
            user_id=user_id,
            message=f"Рекомендую: {result} 🌟\n\nОформляем? 📝✨",
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
                f"🔥 Новый клиент\n"
                f"ID: {user_id}\n"
                f"Воспоминание: {users[user_id].get('memory')}\n"
                f"Ощущение: {users[user_id].get('feel')}\n"
                f"Аромат: {users[user_id].get('smell')}\n"
                f"Предложено: {users[user_id].get('result')}"
            )

            users[user_id]["state"] = "sleep"
            return

        elif text_lower == "попробовать другие ароматы":
            users[user_id]["state"] = "waiting_memory_text"

            vk.messages.send(
                user_id=user_id,
                message="Опиши другое ощущение 😊",
                random_id=0
            )
            return

        else:
            vk.messages.send(
                user_id=user_id,
                message="Нажми кнопку 👇",
                keyboard=get_final_keyboard(),
                random_id=0
            )
            return

    # вне сценария (теперь не триггерится на старте)
    if state is None and users[user_id]["started"]:
        first_name = vk.users.get(user_ids=user_id)[0]["first_name"]

        send_telegram(
            f"⚠️ Вне сценария\n"
            f"{first_name} ({user_id}): {text}"
        )

        users[user_id]["state"] = "sleep"

# ------------------- Webhook -------------------
@app.route("/", methods=["POST"])
def webhook():
    data = request.json

    # подтверждение
    if data["type"] == "confirmation":
        return VK_CONFIRMATION_CODE

    # защита от дублей
    event_id = data.get("event_id")
    if event_id in processed_events:
        return "ok"
    processed_events.add(event_id)

    if data["type"] == "message_new":
        try:
            obj = data["object"]["message"]
            user_id = obj["from_id"]
            text = obj.get("text", "")

            print("USER:", user_id, "TEXT:", text)

            handle_message(user_id, text)

        except Exception as e:
            print("Ошибка:", e)

    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
