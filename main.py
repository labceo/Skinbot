import logging
import sqlite3
import random
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from PIL import Image, ImageDraw
import io

# ==================== НАСТРОЙКИ ====================
API_TOKEN = os.environ.get('API_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# ==================== БАЗА ДАННЫХ ====================
conn = sqlite3.connect('skinbot.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    money INTEGER DEFAULT 1000,
    yen INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    bitcoins INTEGER DEFAULT 0,
    mine_exp INTEGER DEFAULT 0,
    mine_level INTEGER DEFAULT 1,
    current_skin TEXT DEFAULT 'empty',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    item_name TEXT,
    item_category TEXT,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS mine_resources (
    user_id INTEGER PRIMARY KEY,
    iron INTEGER DEFAULT 0,
    gold INTEGER DEFAULT 0,
    diamonds INTEGER DEFAULT 0,
    amethysts INTEGER DEFAULT 0,
    aquamarine INTEGER DEFAULT 0,
    emeralds INTEGER DEFAULT 0,
    matter INTEGER DEFAULT 0,
    plasma INTEGER DEFAULT 0,
    nickel INTEGER DEFAULT 0,
    titanium INTEGER DEFAULT 0,
    cobalt INTEGER DEFAULT 0,
    ectoplasm INTEGER DEFAULT 0,
    palladium INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS business (
    user_id INTEGER PRIMARY KEY,
    territory INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    income INTEGER DEFAULT 100,
    taxes INTEGER DEFAULT 10,
    profit INTEGER DEFAULT 90,
    upgrade_cost INTEGER DEFAULT 1500
)
''')

conn.commit()

# ==================== КУРС РУДЫ ====================
ORE_PRICES = {
    'iron': 800,
    'gold': 10000,
    'diamonds': 50000,
    'amethysts': 100000,
    'aquamarine': 250000,
    'emeralds': 500000,
    'matter': 1000000000,
    'plasma': 4000000000,
    'nickel': 8000000000,
    'titanium': 13000000000,
    'cobalt': 18000000000,
    'ectoplasm': 35000000000,
    'palladium': 80000000000
}

ORE_NAMES = {
    'iron': '⛓ Железо',
    'gold': '🌕 Золото',
    'diamonds': '💎 Алмазы',
    'amethysts': '🎆 Аметисты',
    'aquamarine': '💠 Аквамарин',
    'emeralds': '🍀 Изумруды',
    'matter': '🌌 Материя',
    'plasma': '💥 Плазма',
    'nickel': '🪙 Никель',
    'titanium': '⚙ Титан',
    'cobalt': '🧪 Кобальт',
    'ectoplasm': '☄️ Эктоплазма',
    'palladium': '⚗ Палладий'
}

# ==================== МАГАЗИН ОДЕЖДЫ ====================
SHOP_CATEGORIES = {
    'куртки': {
        'Куртка Alpha industries': 45000,
        'Куртка Thor steinar': 50000,
        'Пуховик Lonsdale': 30000,
        'Куртка Adidas': 15000
    },
    'футболки': {
        'Футболка Lonsdale biglogo': 6000,
        'Футболка Fredperry': 5000,
        'Футболка Thor steinar': 15000,
        'Поло Lonsdale': 8000,
        'Поло Fredperry': 7500
    },
    'кроссовки': {
        'Newbalance 574 (Red)': 13000,
        'Adidas Spezial': 7000,
        'Newbalance 574 (Blue)': 12000,
        'Newbalance 550 (Red)': 15000
    },
    'бомберы': {
        'Бомбер Lonsdale (Blue)': 40000,
        'Бомбер Alpha industries (MA-1)': 50000,
        'Бомбер Pitbull Germany': 75000
    },
    'аксессуары': {
        'Ленточка Alpha industries': 0,
        'Ремень Thor steinar': 0,
        'Пу-3 в руку': 0
    }
}

# ==================== ФУНКЦИИ РАБОТЫ С КОТИКОМ ====================
def create_cat_with_skin(skin_name):
    """
    Создает изображение котика с надетой одеждой
    Если скина нет или 'empty' - возвращает пустого котика
    """
    try:
        # Путь к изображениям
        skins_dir = 'skins'
        cat_path = os.path.join(skins_dir, 'empty_cat.png')
        
        # Проверяем существование папки
        if not os.path.exists(skins_dir):
            os.makedirs(skins_dir)
        
        # Если файла нет, создаем заглушку
        if not os.path.exists(cat_path):
            # Создаем простого котика через PIL
            img = Image.new('RGBA', (400, 600), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            # Рисуем простого котика
            draw.ellipse((150, 100, 250, 200), fill='gray')  # Голова
            draw.ellipse((175, 125, 190, 140), fill='black')  # Левый глаз
            draw.ellipse((210, 125, 225, 140), fill='black')  # Правый глаз
            draw.ellipse((185, 160, 215, 180), fill='pink')   # Нос
            draw.rectangle((170, 200, 230, 400), fill='gray') # Тело
            draw.line((150, 250, 100, 350), fill='gray', width=10)  # Левая рука
            draw.line((250, 250, 300, 350), fill='gray', width=10)  # Правая рука
            draw.line((180, 400, 150, 500), fill='gray', width=10)  # Левая нога
            draw.line((220, 400, 250, 500), fill='gray', width=10)  # Правая нога
            img.save(cat_path)
        
        # Загружаем пустого котика
        cat_img = Image.open(cat_path).convert('RGBA')
        
        # Если нужно надеть скин
        if skin_name and skin_name != 'empty':
            skin_path = os.path.join(skins_dir, f"{skin_name.lower().replace(' ', '_')}.png")
            if os.path.exists(skin_path):
                skin_img = Image.open(skin_path).convert('RGBA')
                # Накладываем одежду на котика
                cat_img = Image.alpha_composite(cat_img, skin_img)
        
        # Сохраняем в байты
        img_bytes = io.BytesIO()
        cat_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes
        
    except Exception as e:
        print(f"Ошибка создания изображения: {e}")
        return None

# ==================== ФУНКЦИИ ПОЛЬЗОВАТЕЛЕЙ ====================
def get_user(user_id, username=None):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute('''
            INSERT INTO users (user_id, username, money, mine_exp, mine_level)
            VALUES (?, ?, 1000, 0, 1)
        ''', (user_id, username))
        
        cursor.execute('''
            INSERT INTO mine_resources (user_id) VALUES (?)
        ''', (user_id,))
        
        cursor.execute('''
            INSERT INTO business (user_id) VALUES (?)
        ''', (user_id,))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    
    return user

def get_money(user_id):
    cursor.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0]

def add_money(user_id, amount):
    cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def remove_money(user_id, amount):
    cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def get_mine_level(user_id):
    cursor.execute("SELECT mine_level FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0]

def add_mine_exp(user_id, exp):
    cursor.execute("UPDATE users SET mine_exp = mine_exp + ? WHERE user_id = ?", (exp, user_id))
    conn.commit()
    
    # Проверка повышения уровня
    cursor.execute("SELECT mine_exp, mine_level FROM users WHERE user_id = ?", (user_id,))
    exp, level = cursor.fetchone()
    
    required = level * 500
    if exp >= required:
        new_level = level + 1
        cursor.execute("UPDATE users SET mine_level = ? WHERE user_id = ?", (new_level, user_id))
        conn.commit()
        return new_level
    return None

def add_resource(user_id, resource, amount):
    cursor.execute(f"UPDATE mine_resources SET {resource} = {resource} + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def get_resources(user_id):
    cursor.execute("SELECT * FROM mine_resources WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def sell_resource(user_id, resource, amount):
    price = ORE_PRICES[resource]
    cursor.execute(f"UPDATE mine_resources SET {resource} = {resource} - ? WHERE user_id = ?", (amount, user_id))
    add_money(user_id, amount * price)
    conn.commit()

def buy_skin(user_id, skin_name, category):
    # Проверяем, есть ли уже такой скин
    cursor.execute("SELECT * FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, skin_name))
    if cursor.fetchone():
        return False
    
    # Получаем цену
    price = SHOP_CATEGORIES[category][skin_name]
    
    # Проверяем деньги
    if get_money(user_id) < price:
        return False
    
    # Покупаем
    remove_money(user_id, price)
    cursor.execute('''
        INSERT INTO inventory (user_id, item_name, item_category)
        VALUES (?, ?, ?)
    ''', (user_id, skin_name, category))
    conn.commit()
    return True

def get_inventory(user_id):
    cursor.execute("SELECT item_name, item_category FROM inventory WHERE user_id = ?", (user_id,))
    return cursor.fetchall()

def set_current_skin(user_id, skin_name):
    cursor.execute("UPDATE users SET current_skin = ? WHERE user_id = ?", (skin_name, user_id))
    conn.commit()

def get_current_skin(user_id):
    cursor.execute("SELECT current_skin FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0]

def get_business(user_id):
    cursor.execute("SELECT * FROM business WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def upgrade_business(user_id):
    business = get_business(user_id)
    territory, level, income, taxes, profit, upgrade_cost = business[1:7]
    
    if get_money(user_id) < upgrade_cost:
        return False
    
    remove_money(user_id, upgrade_cost)
    
    new_territory = territory + 10
    new_level = level + 1
    new_income = income + 50
    new_taxes = taxes + 5
    new_profit = new_income - new_taxes
    new_upgrade_cost = upgrade_cost + 500
    
    cursor.execute('''
        UPDATE business 
        SET territory = ?, level = ?, income = ?, taxes = ?, profit = ?, upgrade_cost = ?
        WHERE user_id = ?
    ''', (new_territory, new_level, new_income, new_taxes, new_profit, new_upgrade_cost, user_id))
    
    conn.commit()
    return True

# ==================== КЛАВИАТУРЫ ====================
def main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👕 Магазин одежды", callback_data="shop_main"),
        InlineKeyboardButton("⛏ Шахта", callback_data="mine_main"),
        InlineKeyboardButton("🏢 Бизнесы", callback_data="business_main"),
        InlineKeyboardButton("💼 Работа", callback_data="work"),
        InlineKeyboardButton("💰 Баланс", callback_data="balance"),
        InlineKeyboardButton("👤 Мой скин", callback_data="show_skin"),
        InlineKeyboardButton("🎒 Инвентарь", callback_data="inventory")
    )
    return keyboard

def shop_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🧥 Куртки", callback_data="shop_куртки"),
        InlineKeyboardButton("👕 Футболки/Поло", callback_data="shop_футболки"),
        InlineKeyboardButton("👟 Кроссовки", callback_data="shop_кроссовки"),
        InlineKeyboardButton("🧥 Бомберы", callback_data="shop_бомберы"),
        InlineKeyboardButton("💍 Аксессуары", callback_data="shop_аксессуары"),
        InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    )
    return keyboard

def mine_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⛏ Копать", callback_data="mine_dig"),
        InlineKeyboardButton("💰 Продать всё", callback_data="mine_sell_all"),
        InlineKeyboardButton("📊 Моя шахта", callback_data="mine_stats"),
        InlineKeyboardButton("📈 Курс руды", callback_data="mine_prices"),
        InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
    )
    return keyboard

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    get_user(user_id, username)
    
    await message.reply(
        "👋 Добро пожаловать в **СкинБот**!\n"
        "Здесь ты можешь покупать одежду для своего котика, "
        "добывать руду и развивать бизнес!\n\n"
        "Используй меню для навигации:",
        reply_markup=main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message_handler(lambda message: message.text and message.text.lower() in ['меню', 'menu', 'скинбот', 'start'])
async def menu_command(message: types.Message):
    await start_command(message)

@dp.callback_query_handler(lambda c: c.data == 'main_menu')
async def main_menu_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "📱 Главное меню:",
        reply_markup=main_keyboard()
    )

# ==================== МАГАЗИН ====================
@dp.callback_query_handler(lambda c: c.data == 'shop_main')
async def shop_main_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "🛒 **Магазин одежды**\nВыбери категорию:",
        reply_markup=shop_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query_handler(lambda c: c.data.startswith('shop_') and c.data != 'shop_main')
async def shop_category_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    category = callback_query.data.replace('shop_', '')
    
    if category not in SHOP_CATEGORIES:
        return
    
    items = SHOP_CATEGORIES[category]
    text = f"🛍 **{category.upper()}**\n\n"
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    for i, (item_name, price) in enumerate(items.items(), 1):
        text += f"{i}. {item_name} - {price}$\n"
        keyboard.add(InlineKeyboardButton(
            f"✅ Купить {item_name}", 
            callback_data=f"buy_{category}_{item_name}"
        ))
    
    keyboard.add(InlineKeyboardButton("◀️ Назад в категории", callback_data="shop_main"))
    
    await bot.send_message(
        callback_query.from_user.id,
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def buy_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    _, category, item_name = callback_query.data.split('_', 2)
    
    # Покупаем скин
    success = buy_skin(user_id, item_name, category)
    
    if not success:
        if get_money(user_id) < SHOP_CATEGORIES[category][item_name]:
            await bot.send_message(user_id, "❌ Недостаточно денег!")
        else:
            await bot.send_message(user_id, "❌ У тебя уже есть этот предмет!")
        return
    
    # Показываем котика с новым скином
    set_current_skin(user_id, item_name)
    img_bytes = create_cat_with_skin(item_name)
    
    if img_bytes:
        await bot.send_photo(
            user_id,
            photo=img_bytes,
            caption=f"✅ Ты купил {item_name}!\n"
                    f"Теперь твой котик выглядит так:"
        )
    else:
        await bot.send_message(
            user_id,
            f"✅ Ты купил {item_name}!\n"
            f"💰 Осталось денег: {get_money(user_id)}$"
        )

# ==================== ШАХТА ====================
@dp.callback_query_handler(lambda c: c.data == 'mine_main')
async def mine_main_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    level = get_mine_level(user_id)
    
    text = (
        "⛏ **Шахта**\n\n"
        f"Твой уровень: {level}\n"
        f"Доступно для добычи:\n"
    )
    
    resources = ['iron', 'gold', 'diamonds', 'amethysts', 'aquamarine', 'emeralds',
                 'matter', 'plasma', 'nickel', 'titanium', 'cobalt', 'ectoplasm', 'palladium']
    
    for i, res in enumerate(resources, 1):
        if i <= level:
            text += f"✓ {ORE_NAMES[res]}\n"
        else:
            text += f"✗ {ORE_NAMES[res]} (уровень {i})\n"
    
    text += "\n⚡ Для добычи напиши: `копать [название]`\n"
    text += "Пример: `копать железо`"
    
    await bot.send_message(
        user_id,
        text,
        reply_markup=mine_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query_handler(lambda c: c.data == 'mine_prices')
async def mine_prices_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    
    text = "📈 **Курс руды**\n\n"
    for ore, price in ORE_PRICES.items():
        text += f"{ORE_NAMES[ore]} - {price}$\n"
    
    await bot.send_message(
        callback_query.from_user.id,
        text,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query_handler(lambda c: c.data == 'mine_stats')
async def mine_stats_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    
    resources = get_resources(user_id)
    cursor.execute("SELECT mine_exp FROM users WHERE user_id = ?", (user_id,))
    exp = cursor.fetchone()[0]
    level = get_mine_level(user_id)
    
    text = f"📊 **Статистика шахты**\n\n"
    text += f"Уровень: {level}\n"
    text += f"Опыт: {exp}/{level * 500}\n\n"
    text += "**Ресурсы:**\n"
    
    # Ресурсы в базе идут в порядке: user_id, iron, gold, diamonds, amethysts, aquamarine, emeralds, matter, plasma, nickel, titanium, cobalt, ectoplasm, palladium
    resource_names = ['iron', 'gold', 'diamonds', 'amethysts', 'aquamarine', 'emeralds',
                     'matter', 'plasma', 'nickel', 'titanium', 'cobalt', 'ectoplasm', 'palladium']
    
    for i, res in enumerate(resource_names, 1):
        amount = resources[i]
        if amount > 0:
            text += f"{ORE_NAMES[res]}: {amount}\n"
    
    if all(resources[i] == 0 for i in range(1, 14)):
        text += "У тебя пока нет ресурсов. Начни добывать!\n"
    
    await bot.send_message(user_id, text, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query_handler(lambda c: c.data == 'mine_dig')
async def mine_dig_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "⚡ Напиши `копать [ресурс]`\n"
        "Например: `копать железо`",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query_handler(lambda c: c.data == 'mine_sell_all')
async def mine_sell_all_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    
    resources = get_resources(user_id)
    resource_names = ['iron', 'gold', 'diamonds', 'amethysts', 'aquamarine', 'emeralds',
                     'matter', 'plasma', 'nickel', 'titanium', 'cobalt', 'ectoplasm', 'palladium']
    
    total = 0
    sold = []
    
    for i, res in enumerate(resource_names, 1):
        amount = resources[i]
        if amount > 0:
            price = ORE_PRICES[res] * amount
            total += price
            cursor.execute(f"UPDATE mine_resources SET {res} = 0 WHERE user_id = ?", (user_id,))
            sold.append(f"{ORE_NAMES[res]}: {amount} шт. на {price}$")
    
    if sold:
        add_money(user_id, total)
        conn.commit()
        
        text = "💰 **Продано:**\n" + "\n".join(sold) + f"\n\nВсего получено: {total}$"
    else:
        text = "❌ У тебя нет ресурсов для продажи!"
    
    await bot.send_message(user_id, text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(lambda message: message.text and message.text.lower().startswith('копать '))
async def dig_command(message: types.Message):
    user_id = message.from_user.id
    level = get_mine_level(user_id)
    
    resource_map = {
        'железо': ('iron', 1),
        'золото': ('gold', 2),
        'алмазы': ('diamonds', 3),
        'алмаз': ('diamonds', 3),
        'аметисты': ('amethysts', 4),
        'аметист': ('amethysts', 4),
        'аквамарин': ('aquamarine', 5),
        'изумруды': ('emeralds', 6),
        'изумруд': ('emeralds', 6),
        'материю': ('matter', 7),
        'материя': ('matter', 7),
        'плазму': ('plasma', 8),
        'плазма': ('plasma', 8),
        'никель': ('nickel', 9),
        'титан': ('titanium', 10),
        'кобальт': ('cobalt', 11),
        'эктоплазму': ('ectoplasm', 12),
        'эктоплазма': ('ectoplasm', 12),
        'палладий': ('palladium', 13)
    }
    
    resource = message.text.lower().replace('копать ', '').strip()
    
    if resource not in resource_map:
        await message.reply("❌ Неизвестный ресурс! Доступно: железо, золото, алмазы, аметисты, аквамарин, изумруды, материя, плазма, никель, титан, кобальт, эктоплазма, палладий")
        return
    
    res_name, req_level = resource_map[resource]
    
    if level < req_level:
        await message.reply(f"❌ Этот ресурс откроется на {req_level} уровне шахты!")
        return
    
    # Добыча
    amount = random.randint(2, 4)
    exp = random.randint(22, 48)
    
    add_resource(user_id, res_name, amount)
    new_level = add_mine_exp(user_id, exp)
    
    response = f"⛏ Ты добыл {amount} {ORE_NAMES[res_name]}!\n"
    response += f"📈 Получено опыта: {exp}\n"
    
    if new_level:
        response += f"🎉 Поздравляю! Твой уровень шахты повышен до {new_level}!"
    
    await message.reply(response)

# ==================== БИЗНЕСЫ ====================
@dp.callback_query_handler(lambda c: c.data == 'business_main')
async def business_main_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    
    business = get_business(user_id)
    territory, level, income, taxes, profit, upgrade_cost = business[1:7]
    
    text = (
        f"🏢 **Твой бизнес**\n\n"
        f"Территория: {territory}м²\n"
        f"Уровень: {level}\n"
        f"Доход: {income}$\n"
        f"Налоги: {taxes}$\n"
        f"Прибыль: {profit}$\n"
        f"Стоимость апгрейда: {upgrade_cost}$\n\n"
        f"[UP] Для следующего уровня: {upgrade_cost}$"
    )
    
    keyboard = InlineKeyboardMarkup()
    if get_money(user_id) >= upgrade_cost:
        keyboard.add(InlineKeyboardButton("📈 Улучшить бизнес", callback_data="business_upgrade"))
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    
    await bot.send_message(
        user_id,
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query_handler(lambda c: c.data == 'business_upgrade')
async def business_upgrade_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    
    success = upgrade_business(user_id)
    
    if success:
        await bot.send_message(user_id, "✅ Бизнес успешно улучшен!")
    else:
        await bot.send_message(user_id, "❌ Недостаточно денег для улучшения!")
    
    # Показываем обновленную информацию
    await business_main_callback(callback_query)

# ==================== РАБОТА ====================
@dp.callback_query_handler(lambda c: c.data == 'work')
async def work_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "⚡ **Скоро в обновлении!** ⚡\n\n"
        "Разработчики уже трудятся над новыми возможностями работы.",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== БАЛАНС ====================
@dp.callback_query_handler(lambda c: c.data == 'balance')
async def balance_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    
    cursor.execute("SELECT money, yen, bank, bitcoins FROM users WHERE user_id = ?", (user_id,))
    money, yen, bank, bitcoins = cursor.fetchone()
    
    text = (
        f"👫 Ник: @{username or 'Не указан'}\n"
        f"💰 Деньги: {money}$\n"
        f"💴 Йены: {yen}¥\n"
        f"🏦 Банк: {bank}$\n"
        f"💽 Биткоины: {bitcoins}🌐"
    )
    
    await bot.send_message(user_id, text)

# ==================== СКИН ====================
@dp.callback_query_handler(lambda c: c.data == 'show_skin')
async def show_skin_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    
    current_skin = get_current_skin(user_id)
    img_bytes = create_cat_with_skin(current_skin)
    
    if img_bytes:
        if current_skin and current_skin != 'empty':
            caption = f"👤 Твой котик в {current_skin}"
        else:
            caption = "👤 Твой голый котик"
        
        await bot.send_photo(user_id, photo=img_bytes, caption=caption)
    else:
        await bot.send_message(user_id, "❌ Ошибка загрузки изображения")

# ==================== ИНВЕНТАРЬ ====================
@dp.callback_query_handler(lambda c: c.data == 'inventory')
async def inventory_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    
    items = get_inventory(user_id)
    
    if not items:
        await bot.send_message(user_id, "🎒 У тебя пока нет купленной одежды.")
        return
    
    text = "🎒 **Твой инвентарь**\n\n"
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for item_name, category in items:
        text += f"• {item_name}\n"
        keyboard.add(InlineKeyboardButton(
            f"👕 Надеть {item_name}",
            callback_data=f"wear_{item_name}"
        ))
    
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="main_menu"))
    
    await bot.send_message(
        user_id,
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query_handler(lambda c: c.data.startswith('wear_'))
async def wear_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    item_name = callback_query.data.replace('wear_', '')
    
    set_current_skin(user_id, item_name)
    img_bytes = create_cat_with_skin(item_name)
    
    if img_bytes:
        await bot.send_photo(
            user_id,
            photo=img_bytes,
            caption=f"✅ Теперь твой котик носит {item_name}!"
        )
    else:
        await bot.send_message(user_id, f"✅ Теперь твой котик носит {item_name}!")

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Создаем папку для скинов
    if not os.path.exists('skins'):
        os.makedirs('skins')
        print("📁 Создана папка 'skins' для изображений")
        print("📌 Положи в неё:")
        print("  - empty_cat.png - пустой котик")
        print("  - Название_скина.png - изображения одежды")
    
    print("🤖 Бот запущен...")
    executor.start_polling(dp, skip_updates=True)
