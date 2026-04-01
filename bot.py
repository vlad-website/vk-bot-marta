import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from dotenv import load_dotenv
import os

load_dotenv()

import requests

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
TOKEN = os.getenv("VK_TOKEN")

users = {}

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

print("Бот запущен...")

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

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = {
        "chat_id": TG_CHAT_ID,
        "text": message
    }
    requests.post(url, data=data)

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_id = event.user_id
        original_text = event.text
        text = event.text.lower()

        print(f"Новое сообщение: {text}")

        # если пользователя ещё нет в словаре
        if user_id not in users:
            users[user_id] = {
                "state": None,
                "started": False
            }

        # если пользователь пишет впервые — отправляем приветствие
        if not users[user_id].get("started"):
            users[user_id]["started"] = True

            vk.messages.send(
                user_id=user_id,
                message=(
                    "Привет, я помощник MN98 🙌🏻\n\n"
                    "Если ты хочешь сделать индивидуальную свечу и выбрать уникальный аромат,напиши слово Memory ✨\n\n"
                    "Или напиши любой интересующий тебя вопрос😊"
                ),
                random_id=0
            )

            continue

        # текущее состояние
        state = users[user_id]["state"]

        # режим сна (менеджер общается)
        if state == "sleep":
            if text == "memory":
                users[user_id]["state"] = None
            else:
                continue

        # 1. старт
        if "memory" in text or "мемори" in text:
            users[user_id]["state"] = "waiting_memory_text"

            # получаем имя пользователя
            user_info = vk.users.get(user_ids=user_id)[0]
            first_name = user_info["first_name"]

            vk.messages.send(
                user_id=user_id,
                message=(
                    f"Хорошо, {first_name}!\n\n"
                    "Давай попробуем найти твой Memory Number\n"
                    "Я задам пару простых вопросов:\n\n"
                    "Скажи, какой момент или ощущение тебе сейчас ближе всего?\n"
                    "(Это может быть что угодно — место, время, чувство)"
                ),
                random_id=0
            )

        # 2. пользователь отправил воспоминание
        elif state == "waiting_memory_text":
            users[user_id]["memory"] = original_text
            users[user_id]["state"] = "waiting_feel"

            vk.messages.send(
                user_id=user_id,
                message="Отлично! Скажи пожалуйста, как ты ощущаешь: это что-то теплое, или свежее?",
                keyboard=get_feel_keyboard(),
                random_id=0
            )

        elif state == "waiting_feel":
            if text in ["теплое ощущение", "свежее ощущение"]:
                users[user_id]["feel"] = text
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
                    message="Не совсем понимаю 😅 Выбери один из вариантов на кнопках ниже:",
                    keyboard=get_feel_keyboard(),
                    random_id=0
                )


        elif state == "waiting_smell":
            if text not in ["сладкий", "древесный", "цветочный"]:
                vk.messages.send(
                    user_id=user_id,
                    message="Не совсем понимаю 😅 Выбери один из вариантов на кнопках ниже:",
                    keyboard=get_smell_keyboard(),
                    random_id=0
                )
                continue

            users[user_id]["smell"] = text

            feel = users[user_id]["feel"]
            smell = text

            # логика подбора
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

        elif state == "final_choice":
            if text == "да, давайте":
                vk.messages.send(
                    user_id=user_id,
                    message=(
                        "Отлично! Сейчас с вами свяжется менеджер 😊\n\n"
                        "Если захочешь подобрать другой аромат — напиши memory ✨"
                    ),
                    random_id=0
                )

                # Telegram уведомление
                send_telegram(
                    f"Новый клиент!\n"
                    f"ID: {user_id}\n"
                    f"Воспоминание: {users[user_id].get('memory')}\n"
                    f"Ощущение: {feel}\n"
                    f"Аромат: {smell}\n"
                    f"Предложено: {result}"
                )
                users[user_id]["state"] = "sleep"

            elif text == "попробовать другие ароматы":
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

        elif state is None:
            # получаем имя пользователя
            user_info = vk.users.get(user_ids=user_id)[0]
            first_name = user_info["first_name"]

            send_telegram(
                f"⚠️ Клиент написал вне сценария\n\n"
                f"Имя: {first_name}\n"
                f"ID: {user_id}\n"
                f"Сообщение: {original_text}"
            )
            users[user_id]["state"] = "sleep"