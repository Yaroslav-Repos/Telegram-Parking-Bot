import asyncio
import random
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import numpy as np
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import os
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()

# Отримання змінних
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

if not MONGO_URI:
    raise ValueError("NO MONGO_URI!")

#Підключення до MongoDB через motor
client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB]
users_collection = db["users"]
parking_collection = db["parking"]

#Константа кількості парко-місць
PARKING_SLOTS = {1: 32, 2: 20, 3: 26}

#Параметри розподілу
LAMBDA_ARRIVAL = 1/30   #середній інтервал між приїздами 30 сек
PARK_TIME_MEAN = 30     #середній час стоянки (с)
PARK_TIME_STDDEV = 10   #стандартне відхилення середнього часу стоянки
POISSON_LAMBDA = 3      #машин в середньому за один приїзд

#Семафор для обмеження 30 одночасних паркувальників
MAX_ACTIVE_CARS = 30
semaphore = asyncio.Semaphore(MAX_ACTIVE_CARS)

#Глобальна змінна для збереження даних про заповненість паркувальних місць
parking_data = {} 

#Визначення часу логування подій
def timestamp():
    return datetime.now().strftime("[%H:%M:%S]")

#Симуляція приїзду та виїзду машини, обробник паркування машини
async def handle_car():
    async with semaphore:
        lot_number = random.choice(list(PARKING_SLOTS.keys()))
        num_slots = PARKING_SLOTS[lot_number]

        #Перевірка вільних місць
        occupied_slots = {
            slot["slot"] for slot in await parking_collection.find({"lot": lot_number, "user_id": {"$ne": None}}).to_list(length=None)
        }
        available_slot = next((i for i in range(1, num_slots + 1) if i not in occupied_slots), None)

        if available_slot:
            #Паркування випадкового користувача якщо вільні місця є
            user_id = random.randint(1000, 9999)
            await users_collection.insert_one({
                "user_id": user_id,
                "balance": 50,
                "parked": {"lot": lot_number, "slot": available_slot}
            })
            await parking_collection.update_one(
                {"lot": lot_number, "slot": available_slot},
                {"$set": {"user_id": user_id}},
                upsert=True
            )
            print(f"\n{timestamp()} Машина користувача {user_id} припаркована: майданчик {lot_number}, місце {available_slot}")
            #Оновлення даних для графіка після паркування
            parking_data[lot_number] += 1

            #Час стоянки, визначається за нормальним розподілом
            park_time = max(5, int(random.normalvariate(PARK_TIME_MEAN, PARK_TIME_STDDEV)))
            await asyncio.sleep(park_time)

            #Виїзд після закінчення часу стоянки
            await parking_collection.update_one(
                {"lot": lot_number, "slot": available_slot},
                {"$set": {"user_id": None}}
            )
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"parked": None}}
            )
            print(f"\n{timestamp()} Машина користувача {user_id} виїхала з майданчика {lot_number}, місце {available_slot}, час стоянки: {park_time} сек")
            #Оновлення даних для графіка після виїзду
            parking_data[lot_number] -= 1

        else:
            print(f"\n{timestamp()} Немає місць на майданчику {lot_number}")

#Функція для малювання графіка з "корзинами"
def plot_parking():
    global parking_data
    fig, ax = plt.subplots()
    lot_numbers = list(parking_data.keys())
    def update_graph(frame):
        ax.clear()
        #Дані для графіку
        filled_slots = [parking_data[lot] for lot in lot_numbers]
        free_slots = [PARKING_SLOTS[lot] - filled_slots[i] for i, lot in enumerate(lot_numbers)]
        #Графік заповненості
        ax.bar(lot_numbers, filled_slots, width=0.5, color='blue', label="Заповнено")
        ax.bar(lot_numbers, free_slots, width=0.5, bottom=filled_slots, color='gray', label="Вільно")

        #Підписи та межі осей
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 32)
        ax.set_xlabel('Майданчики')
        ax.set_ylabel('Заповнені місця')
        ax.set_title('Статистика паркування')
        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels(['Майданчик 1', 'Майданчик 2', 'Майданчик 3'])
        ax.legend()

    ani = FuncAnimation(fig, update_graph, interval=1000)
    plt.show()

#Виведення статистики
async def parking_statistics():
    global parking_data
    print(f"\n{timestamp()} Статистика паркування:")
    #Отримуємо статистику для кожного майданчика паралельно та обчислюємо заповненість
    stats = await asyncio.gather(
        *[
            #Розпаковка об'єктів із заповненням паркомісць одночасно
            parking_collection.count_documents({"lot": lot_number, "user_id": {"$ne": None}})
            for lot_number in PARKING_SLOTS
        ]
    )
    #Виведення результатів
    for i, lot_number in enumerate(PARKING_SLOTS.keys()):
        occupied = stats[i]
        free = PARKING_SLOTS[lot_number] - occupied
        print(f"\tМайданчик {lot_number}: Заповнено {occupied}, Вільно {free}")
    print()

#Початкове наповнення даних про заповненість паркувальних місць з бази даних
async def initialize_parking_data():
    global parking_data
    parking_data = {}
    for lot_number in PARKING_SLOTS.keys():
        count = await parking_collection.count_documents({"lot": lot_number, "user_id": {"$ne": None}})
        parking_data[lot_number] = count

#Основний цикл
async def main_loop():
    await initialize_parking_data()
    await parking_statistics()
    #Запускаємо графік у окремому потоці
    threading.Thread(target=plot_parking, daemon=True).start()

    while True:
        #Визначаємо кількість автомобілів на паркування за розподілом Пуассона
        num_arrivals = np.random.poisson(lam=POISSON_LAMBDA)
        print(f"\n{timestamp()} Зафіксовано прибуття: {num_arrivals} машин(и) паркуються")
        for _ in range(num_arrivals):
            asyncio.create_task(handle_car()) #Запускаємо машину як окрему задачу

        #Експоненційно розподілений час до наступної події
        interval = random.expovariate(LAMBDA_ARRIVAL)
        await asyncio.sleep(interval)
        await parking_statistics()

# Запуск програми
if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nСимуляція зупинена.")
