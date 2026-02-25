import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand, BotCommandScopeDefault, ReplyKeyboardMarkup, KeyboardButton
from pymongo import MongoClient


load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

if not TOKEN:
    raise ValueError("NO BOT_TOKEN!")
if not MONGO_URI:
    raise ValueError("NO MONGO_URI!")


client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
users_collection = db["users"]
parking_collection = db["parking"]


class User:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.data = users_collection.find_one({"user_id": self.user_id})

    def exists(self):
        return self.data is not None

    def register(self):
        if not self.exists():
            users_collection.insert_one({"user_id": self.user_id, "balance": 0, "parked": None})
            self.data = users_collection.find_one({"user_id": self.user_id})

    def get_balance(self):
        self.data = users_collection.find_one({"user_id": self.user_id})
        return self.data.get("balance", 0)

    def update_balance(self, amount: int):
        users_collection.update_one({"user_id": self.user_id}, {"$inc": {"balance": amount}})
        self.data = users_collection.find_one({"user_id": self.user_id})

    def is_parked(self):
        self.data = users_collection.find_one({"user_id": self.user_id})
        return self.data.get("parked") is not None

    def park(self, lot: int, slot: int):
        users_collection.update_one({"user_id": self.user_id}, {"$set": {"parked": {"lot": lot, "slot": slot}}})
        parking_collection.update_one({"lot": lot, "slot": slot}, {"$set": {"user_id": self.user_id}}, upsert=True)

    def exit_parking(self):
        if self.is_parked():
            lot, slot = self.data["parked"]["lot"], self.data["parked"]["slot"]
            users_collection.update_one({"user_id": self.user_id}, {"$set": {"parked": None}})
            parking_collection.update_one({"lot": lot, "slot": slot}, {"$set": {"user_id": None}})
            return lot, slot
        return None, None


class ParkingLot:
    def __init__(self, lot_number: int, max_slots: int):
        self.lot_number = lot_number
        self.max_slots = max_slots

    def get_occupied_slots(self):
        return {slot["slot"] for slot in parking_collection.find({"lot": self.lot_number, "user_id": {"$ne": None}})}

    def get_available_slot(self):
        occupied = self.get_occupied_slots()
        return next((i for i in range(1, self.max_slots + 1) if i not in occupied), None)


class ParkingBot:
    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.main_menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔑 Реєстрація"), KeyboardButton(text="🚗 Паркуватися")],
                [KeyboardButton(text="💳 Поповнити баланс"), KeyboardButton(text="🚪 Виїзд")]
            ],
            resize_keyboard=True
        )
        self.lots_config = {1: 31, 2: 21, 3: 27}
        self.register_handlers()

    async def set_commands(self):
        commands = [BotCommand(command="/start", description="Старт бота")]
        await self.bot.set_my_commands(commands, BotCommandScopeDefault())

    def register_handlers(self):
        self.dp.message.register(self.start_command, Command(commands=["start"]))
        self.dp.message.register(self.register_user_command, lambda m: m.text == "🔑 Реєстрація")
        self.dp.message.register(self.add_balance_command, lambda m: m.text == "💳 Поповнити баланс")
        self.dp.message.register(self.park_car_command, lambda m: m.text == "🚗 Паркуватися")
        self.dp.message.register(self.choose_parking_lot_command, lambda m: m.text in ["1-й майданчик", "2-й майданчик", "3-й майданчик"])
        self.dp.message.register(self.exit_parking_command, lambda m: m.text == "🚪 Виїзд")

    # Handlers
    async def start_command(self, message: types.Message):
        await message.answer("Вітаємо у системі паркування!", reply_markup=self.main_menu)

    async def register_user_command(self, message: types.Message):
        user = User(message.from_user.id)
        if user.exists():
            await message.answer("Ви вже зареєстровані!", reply_markup=self.main_menu)
        else:
            user.register()
            await message.answer("Реєстрація успішна! Поповніть баланс для паркування.", reply_markup=self.main_menu)

    async def add_balance_command(self, message: types.Message):
        user = User(message.from_user.id)
        if not user.exists():
            await message.answer("Ви не зареєстровані! Спочатку зареєструйтесь.", reply_markup=self.main_menu)
            return
        user.update_balance(50)
        await message.answer(f"Баланс поповнено! Ваш баланс: {user.get_balance()} грн.", reply_markup=self.main_menu)

    async def park_car_command(self, message: types.Message):
        user = User(message.from_user.id)
        if not user.exists():
            await message.answer("Ви не зареєстровані! Спочатку зареєструйтесь.", reply_markup=self.main_menu)
            return
        if user.get_balance() < 50:
            await message.answer("Недостатньо коштів для паркування. Поповніть баланс!", reply_markup=self.main_menu)
            return
        if user.is_parked():
            await message.answer("Ви вже припарковані!", reply_markup=self.main_menu)
            return

        park_menu = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=f"{i}-й майданчик")] for i in self.lots_config.keys()],
            resize_keyboard=True
        )
        await message.answer("Оберіть паркувальний майданчик:", reply_markup=park_menu)

    async def choose_parking_lot_command(self, message: types.Message):
        user = User(message.from_user.id)
        if user.is_parked():
            await message.answer("Ви вже припарковані!", reply_markup=self.main_menu)
            return

        lot_number = int(message.text[0])
        lot = ParkingLot(lot_number, self.lots_config[lot_number])
        available_slot = lot.get_available_slot()

        if available_slot:
            user.park(lot_number, available_slot)
            user.update_balance(-50)
            await message.answer(f"Ви припаркувалися на місці {available_slot} майданчика {lot_number}.", reply_markup=self.main_menu)
        else:
            await message.answer("На цьому майданчику немає вільних місць.", reply_markup=self.main_menu)

    async def exit_parking_command(self, message: types.Message):
        user = User(message.from_user.id)
        if not user.exists():
            await message.answer("Ви не зареєстровані!", reply_markup=self.main_menu)
            return
        if not user.is_parked():
            await message.answer("Ви не припарковані.", reply_markup=self.main_menu)
            return

        lot, slot = user.exit_parking()
        await message.answer(f"Ви покинули місце {slot} майданчика {lot}.", reply_markup=self.main_menu)

    async def run(self):
        await self.set_commands()
        await self.dp.start_polling(self.bot, skip_updates=True)


# Entry point
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot_app = ParkingBot(TOKEN)
    asyncio.run(bot_app.run())