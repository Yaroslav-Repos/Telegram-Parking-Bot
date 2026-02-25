import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram.types import BotCommand, BotCommandScopeDefault 
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from pymongo import MongoClient

# Завантаження змінних середовища
load_dotenv()

# Отримання змінних
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

# Перевірка наявності змінних
if not TOKEN:
    raise ValueError("NO BOT_TOKEN!")
if not MONGO_URI:
    raise ValueError("NO MONGO_URI!")

# Підключення до MongoDB
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
users_collection = db["users"]
parking_collection = db["parking"]

# Налаштування aiogram
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Функція для встановлення меню команд бота
async def set_commands():
    commands = [
        BotCommand(command="/start", description="Старт бота")
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())

#Функції пошуку користувача в MongoDB
def get_user(user_id):
    return users_collection.find_one({"user_id": user_id})

#Функції реєстрації користувача, шляхом запису в колекцію MongoDB
def register_user(user_id):
    if not get_user(user_id):
        users_collection.insert_one({"user_id": user_id, "balance": 0, "parked": None})

#Функції оновлення балансу користувача
def update_balance(user_id, amount):
    users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})

#Встановлення у MongoDB майданчика та місця парковки користувача
def park_user(user_id, lot_number, slot_number):
    users_collection.update_one({"user_id": user_id}, {"$set": {"parked": {"lot": lot_number, "slot": slot_number}}})
    parking_collection.update_one(
        {"lot": lot_number, "slot": slot_number},
        {"$set": {"user_id": user_id}},
        upsert=True
    )

#Оновлення даних про виїзд користувача, звільнення парко-місця у базі даних
def exit_parking(user_id):
    user = get_user(user_id)
    if user and user.get("parked"):
        lot, slot = user["parked"]["lot"], user["parked"]["slot"]
        users_collection.update_one({"user_id": user_id}, {"$set": {"parked": None}})
        parking_collection.update_one({"lot": lot, "slot": slot}, {"$set": {"user_id": None}})

#Кнопки головного меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔑 Реєстрація"), KeyboardButton(text="🚗 Паркуватися")],
        [KeyboardButton(text="💳 Поповнити баланс"), KeyboardButton(text="🚪 Виїзд")]
    ],
    resize_keyboard=True
)

#Команда "Старт", привітання користувача
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Вітаємо у системі паркування!", reply_markup=main_menu)

@dp.message(lambda message: message.text == "🔑 Реєстрація")
async def register_user_command(message: types.Message):
    user_id = message.from_user.id
    if get_user(user_id):
        await message.answer("Ви вже зареєстровані!", reply_markup=main_menu)
    else:
        register_user(user_id)
        await message.answer("Реєстрація успішна! Поповніть баланс для паркування.", reply_markup=main_menu)

@dp.message(lambda message: message.text == "💳 Поповнити баланс")
async def add_balance(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("Ви не зареєстровані! Спочатку зареєструйтесь.", reply_markup=main_menu)
        return
    update_balance(user_id, 50)
    user = get_user(user_id)
    await message.answer(f"Баланс поповнено! Ваш баланс: {user['balance']} грн.", reply_markup=main_menu)

@dp.message(lambda message: message.text == "🚗 Паркуватися")
async def park_car(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer("Ви не зареєстровані! Спочатку зареєструйтесь.", reply_markup=main_menu)
        return
    if user["balance"] < 50:
        await message.answer("Недостатньо коштів для паркування. Поповніть баланс!", reply_markup=main_menu)
        return
    if user["parked"] is not None:
        await message.answer("Ви вже припарковані!", reply_markup=main_menu)
        return

    park_menu = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1-й майданчик")],
            [KeyboardButton(text="2-й майданчик")],
            [KeyboardButton(text="3-й майданчик")]
        ],
        resize_keyboard=True)
    await message.answer("Оберіть паркувальний майданчик:", reply_markup=park_menu)

@dp.message(lambda message: message.text in ["1-й майданчик", "2-й майданчик", "3-й майданчик"])
async def choose_parking_lot(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user["parked"] is not None:
        await message.answer("Ви вже припарковані!", reply_markup=main_menu)
        return

    lot_number = int(message.text[0])  # Отримуємо номер майданчика
    occupied_slots = parking_collection.find({"lot": lot_number, "user_id": {"$ne": None}})
    occupied_slots = {slot["slot"] for slot in occupied_slots}

    n = 0
    if lot_number == 1:
        n = 31
    if lot_number == 2:
        n = 21
    if lot_number == 3:
        n = 27

    available_slot = next((i for i in range(1, n) if i not in occupied_slots), None)
    
    if available_slot:
        park_user(user_id, lot_number, available_slot)
        update_balance(user_id, -50)
        await message.answer(f"Ви припаркувалися на місці {available_slot} майданчика {lot_number}.", reply_markup=main_menu)
    else:
        await message.answer("На цьому майданчику немає вільних місць.", reply_markup=main_menu)

@dp.message(lambda message: message.text == "🚪 Виїзд")
async def exit_parking_command(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        await message.answer("Ви не зареєстровані!", reply_markup=main_menu)
        return
    if user["parked"] is None:
        await message.answer("Ви не припарковані.", reply_markup=main_menu)
        return

    lot_number, slot_number = user["parked"]["lot"], user["parked"]["slot"]
    exit_parking(user_id)
    await message.answer(f"Ви покинули місце {slot_number} майданчика {lot_number}.", reply_markup=main_menu)

async def main():
    await set_commands() 
    await dp.start_polling(bot, skip_updates=True)  # Запуск бота для обробки повідомлень

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

