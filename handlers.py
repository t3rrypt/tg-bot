import asyncio
import sqlite3
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

import json
import kb
import price
import re
import os

load_dotenv()

router = Router()

admins = list(map(int, os.getenv("ADMINS", "").split(","))) # Список ID всех админов
requisite_path = "requisite.json" # Файл с реквизитом
active_deals = {} # Активные сделки
cancel_text = '❌ Отмена' # Текст для кнопки

class CryptoBuy(StatesGroup): # Все состояния пользователя
    waiting_for_amount_btc = State()
    waiting_for_amount_usdt = State()
    waiting_for_amount_ltc = State()

    wallet = State()
    payment_method = State()
    waiting_for_code = State()
    waiting_for_screenshot = State()
    waiting_for_payment = State()

    waiting_for_requisite = State()
    waiting_for_new_promocode = State()
    waiting_for_discount = State()
    waiting_for_num_of_activations = State()

# Фунцкия для сохранения новых пользователей в базу данных
def save_user(message):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute('SELECT * FROM users WHERE id = ?', (message.from_user.id,))
    user = cur.fetchone()
    if user:
        pass
    else:
        cur.execute('INSERT INTO users(username, id) VALUES(?, ?)',('@' + message.from_user.username or 'NULL', message.from_user.id))
        con.commit()
        cur.close()
        con.close()

def save_promocode(promocode, num_of_activations, discount):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute('INSERT OR IGNORE INTO promocodes(promocode, num_of_activations, discount) VALUES(?, ?, ?)',(promocode, num_of_activations, discount))
    con.commit()
    cur.close()
    con.close()

def check_promocode(promocode):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute('SELECT * FROM promocodes WHERE promocode = ?', (promocode,))
    code = cur.fetchone()
    if code:
        cur.execute("UPDATE promocodes SET num_of_activations = num_of_activations - 1 WHERE promocode = ? AND num_of_activations > 0", (code[0],))
        if cur.rowcount == 0:
            cur.close()
            con.close()
            return False, "❌ Промокод не найден или больше не активен."
        else:
            cur.execute('SELECT * FROM promocodes WHERE promocode = ?', (promocode,))
            con.commit()
            cur.close()
            con.close()
            return True, "✅ Промокод успешно применён.", code[2]


# Функция для получения реквизита
def get_requisite():
    if not os.path.exists(requisite_path):
        return None
    with open(requisite_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        requisite = data.get("payment_method")
        if not requisite:
            return None
        else:
            return ' '.join(requisite[i:i+4] for i in range(0, len(requisite), 4))

# Обработка /start
@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(f'Добро пожаловать, {message.chat.first_name}!\n\nВыберите одну из кнопок ниже', reply_markup=kb.start_kb)
        save_user(message)
    else:
        pass

# --- Обработка кнопок для покупки валют ---
@router.message(F.text == 'Купить BTC')
async def buy_btc(message: Message, state: FSMContext):
    if await state.get_state() != CryptoBuy.waiting_for_payment:
        await message.answer(f"Приблизительный курс BTC: {price.get_price_btc():.2f}₽\n\nВведите сумму в рублях:\nПример: 5000",reply_markup=kb.cancel_kb)
        await state.set_state(CryptoBuy.waiting_for_amount_btc)
    else:
        await message.answer('⚠️ У вас уже есть активная сделка! ⚠️\nСначала завершите её.')

@router.message(F.text == 'Купить USDT')
async def buy_usdt(message: Message, state: FSMContext):
    if await state.get_state() != CryptoBuy.waiting_for_payment:
        await message.answer(f"Приблизительный курс USDT: {price.get_price_usdt():.1f}₽\n\nВведите сумму в рублях:\nПример: 5000",reply_markup=kb.cancel_kb)
        await state.set_state(CryptoBuy.waiting_for_amount_usdt)
    else:
        await message.answer('⚠️ У вас уже есть активная сделка! ⚠️\nСначала завершите её.')

@router.message(F.text == 'Купить LTC')
async def buy_ltc(message: Message, state: FSMContext):
    if await state.get_state() != CryptoBuy.waiting_for_payment:
        await message.answer(f"Приблизительный курс LTC: {price.get_price_ltc():.2f}₽\n\nВведите сумму в рублях:\nПример: 5000", reply_markup=kb.cancel_kb)
        await state.set_state(CryptoBuy.waiting_for_amount_ltc)
    else:
        await message.answer('⚠️ У вас уже есть активная сделка! ⚠️\nСначала завершите её.')

# --- Обработка количества покупаемой валюты ---
@router.message(CryptoBuy.waiting_for_amount_btc, F.text.regexp(r"^\d+([.,]\d{1,2})?$"))
async def process_amount(message: Message, state: FSMContext):
    message_text = message.text.replace(",", ".")
    cost = float(message_text)
    if float(cost) < 1000:
        await message.answer('Минимальная сумма покупки 1000 рублей!')
    else:
        cost = float(message.text)
        amount = float(cost) / float(price.get_price_btc())
        await message.answer(f"Сумма к оплате:\n\n{cost}₽ + комиссия (зависит от метода оплаты)\nВы получите {amount} BTC\n\n❗Продолжая использование бота, вы подтверждаете, что ознакомлены и соглашаетесь с условиями Пользовательского соглашения.👇", reply_markup=kb.user_agreement)
        await message.answer(f"Введите BTC адрес для отправки средств", reply_markup=kb.cancel_kb)
        await state.update_data(amount=amount, cost=cost, currency="BTC")
        await state.set_state(CryptoBuy.wallet)

@router.message(CryptoBuy.waiting_for_amount_usdt, F.text.regexp(r"^\d+([.,]\d{1,2})?$"))
async def process_amount(message: Message, state: FSMContext):
    message_text = message.text.replace(",", ".")
    cost = float(message_text)
    if float(cost) < 1000:
        await message.answer('Минимальная сумма покупки 1000 рублей!')
    else:
        cost = float(message.text)
        amount = float(cost) / float(price.get_price_usdt())
        await message.answer(f"Сумма к оплате:\n\n{cost}₽ + комиссия (зависит от метода оплаты)\nВы получите {amount} USDT\n\n️❗Продолжая использование бота, вы подтверждаете, что ознакомлены и соглашаетесь с условиями Пользовательского соглашения.👇", reply_markup=kb.user_agreement)
        await message.answer(f"Введите USDT адрес для отправки средств", reply_markup=kb.cancel_kb)
        await state.update_data(amount=amount, cost=cost, currency="USDT")
        await state.set_state(CryptoBuy.wallet)

@router.message(CryptoBuy.waiting_for_amount_ltc, F.text.regexp(r"^\d+([.,]\d{1,2})?$"))
async def process_amount(message: Message, state: FSMContext):
    message_text = message.text.replace(",", ".")
    cost = float(message_text)
    if float(cost) < 1000:
        await message.answer('Минимальная сумма покупки 1000 рублей!')
    else:
        cost = float(message.text)
        amount = float(cost) / float(price.get_price_ltc())
        await message.answer(f"Сумма к оплате:\n\n{cost}₽ + комиссия (зависит от метода оплаты)\nВы получите {amount} LTC\n\n❗Продолжая использование бота, вы подтверждаете, что ознакомлены и соглашаетесь с условиями Пользовательского соглашения.👇", reply_markup=kb.user_agreement)
        await message.answer(f"Введите LTC адрес для отправки средств", reply_markup=kb.cancel_kb)
        await state.update_data(amount=amount, cost=cost, currency="LTC")
        await state.set_state(CryptoBuy.wallet)


# Функция для получения крипто-кошелька
@router.message(CryptoBuy.wallet)
async def process_wallet(message: Message, state: FSMContext):
    wallet = message.text.strip()

    if wallet == cancel_text:
        await state.clear()
        await start(message, state)
        return
    elif re.search(r'[^\x00-\x7F]', wallet):
        await message.answer("❌ Введите корректный адрес!")
        return

    await state.update_data(wallet=wallet)
    await message.answer('Введите промокод.\n\nЕсли у Вас его нет, нажмите на кнопку ниже.', reply_markup=kb.no_promocode_kb)
    await state.set_state(CryptoBuy.waiting_for_code)

@router.message(CryptoBuy.waiting_for_code)
async def procces_promocode(message: Message, state: FSMContext):
    promocode = message.text.strip()

    if promocode == '🎟 Нет промокода.':
        await state.set_state(CryptoBuy.payment_method)
        await message.answer('Выберите способ оплаты:', reply_markup=kb.payment_kb)
        return
    else:
        data = check_promocode(promocode)
        if data[0]:
            await message.answer(data[1])
            await state.update_data(discount=data[2])
            await state.update_data(promocode=promocode)
            await state.set_state(CryptoBuy.payment_method)
            await message.answer('Выберите способ оплаты:', reply_markup=kb.payment_kb)
            return
        else:
            await message.answer(data[1], reply_markup=kb.no_promocode_kb)

# Обработка кнопок с выбором метода оплаты
@router.message(CryptoBuy.payment_method, F.text.in_([f"💳 Оплата картой СНГ ({kb.commission_card}%)", f"🏦 Оплата по СБП ({kb.commission_sbp}%)"]))
async def process_payment_method(message: Message, state: FSMContext, bot):
    payment_method = message.text
    await state.update_data(payment_method=payment_method)
    data = await state.get_data()

    # Сохранение информации о заказе
    amount = data.get("amount")
    cost = data.get("cost")
    currency = data.get("currency")
    wallet = data.get("wallet")
    payment_method = data.get("payment_method")
    promocode = data.get("promocode") or None
    discount = data.get("discount") or None

    data = kb.which_payment_method(amount, currency, cost, wallet, payment_method, promocode, discount, get_requisite()) # Вызов функции для получение текста, кнопок и ID заказа
    await message.answer(f'Метод оплаты выбран: {payment_method}', reply_markup=ReplyKeyboardRemove())
    await message.answer(text=data[0], reply_markup=data[1] or None, parse_mode='HTML')
    await state.clear()
    await state.set_state(CryptoBuy.waiting_for_payment)

    # Запуск таймера в 15 минут и создание сделки
    task = asyncio.create_task(payment_timer(message, state, bot, data[2]))
    active_deals[message.chat.id] = task

    # Рассылка сообщение о новой сделки админам
    for admin_id in admins:
        try:
            await message.bot.send_message(admin_id, f'Пользователь @{message.chat.username or message.chat.id} создал заказ!\n<code>{amount:.8f}</code> {currency}\n<code>{data[3]:.2f}</code> рублей.\nПромокод: {promocode if promocode else 'Нет'} на скидку {discount if discount else 0}%\nАдрес для получения: <code>{wallet}</code>\n\nСпособ оплаты: {payment_method}\n\n<i>ID заказа: <code>{data[2]}</code></i>', parse_mode='HTML', reply_markup=kb.get_complete_btn(message))
        except Exception as e:
            print(f"Не удалось отправить сообщение администратору {admin_id}: {e}")

# Проверка на правильное написание суммы пользователем
@router.message(CryptoBuy.waiting_for_amount_btc, CryptoBuy.waiting_for_amount_usdt, CryptoBuy.waiting_for_amount_ltc)
async def reject_anything_else(message: Message):
    await message.answer("Неверный ввод, введите корректную сумму.")

# Функция для отправки чека от пользователя админам
@router.message(CryptoBuy.waiting_for_screenshot)
async def process_screenshot(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id

    await message.answer("Чек успешно отправлен! 🧾")
    await state.clear()

    # Рассылка чека админам
    for admin_id in admins:
        try:
            await message.bot.send_photo(admin_id, photo=photo_id, caption=f'Чек от пользователя @{message.chat.username or message.chat.id}')
        except Exception as e:
            print(f"Не удалось отправить сообщение администратору {admin_id}: {e}")

# Обработчик команды /setcard для установки новых реквизитов
@router.message(Command('setcard'))
async def set_card(message: Message, state: FSMContext):
    for admin_id in admins:
        if message.chat.id == admin_id:
            await message.answer(f"Введите новые реквизиты", reply_markup=kb.cancel_kb)
            await state.set_state(CryptoBuy.waiting_for_requisite)
        else:
            await message.answer(f"🚫 У вас нет доступа к этой команде!")

# Обработка реквизитов написанных админом
@router.message(CryptoBuy.waiting_for_requisite)
async def new_requisite(message: Message, state: FSMContext):
    requisite = message.text.replace(" ", "")
    if requisite.isdigit(): # Проверка на то, являются ли написанные админом реквизиты числом
        await state.clear()
        with open(requisite_path, "w", encoding="utf-8") as f:
            json.dump({"payment_method": requisite}, f, ensure_ascii=False)
        await message.answer(f"✅ Новые реквизиты успешно сохранены!\n{get_requisite()}")
        await start(message, state)
    elif message.text == cancel_text: # Если админ нажал кнопку "Отмена"
        await message.answer(f"🚫 Действие отменено!")
        await state.clear()
        await start(message, state)
    else: # Если введено что-то кроме цифр
        await message.answer('❌ Введите корректные реквизиты!')

# Обработчик команды /newpromo
@router.message(Command('newpromo'))
async def new_promocode(message: Message, state: FSMContext):
    for admin_id in admins:
        if message.chat.id == admin_id:
            await message.answer('Введите новый промокод', reply_markup=kb.cancel_kb)
            await state.set_state(CryptoBuy.waiting_for_new_promocode)
        else:
            await message.answer(f"🚫 У вас нет доступа к этой команде!")

@router.message(CryptoBuy.waiting_for_new_promocode)
async def procces_new_promocode(message: Message, state: FSMContext):
    promocode = message.text
    if promocode != cancel_text:
        await state.update_data(promocode=promocode)
        await message.answer('Введите % скидки', reply_markup=kb.cancel_kb)
        await state.set_state(CryptoBuy.waiting_for_discount)
    else:
        await message.answer('Отменено.')
        await state.clear()
        await start(message, state)

@router.message(CryptoBuy.waiting_for_discount)
async def get_discount(message: Message, state: FSMContext):
    discount = int(message.text)
    await state.update_data(discount=discount)
    await state.set_state(CryptoBuy.waiting_for_new_promocode)
    await message.answer('Введите количество активаций', reply_markup=kb.cancel_kb)
    await state.set_state(CryptoBuy.waiting_for_num_of_activations)

@router.message(CryptoBuy.waiting_for_num_of_activations)
async def add_promocode(message: Message, state: FSMContext):
    num = int(message.text)
    promocode = await state.get_data()
    save_promocode(promocode["promocode"], num, promocode["discount"])
    await message.answer(f'Промокод: <code>{promocode["promocode"]}</code>\nСкидка: {promocode["discount"]}%\nКоличество активаций: {num}\n\n<b>✅ Промокод успешно создан!</b>\n<i>Если такой промокод уже существует, то он не был доабвлен</i>', parse_mode='HTML')
    await state.clear()
    await start(message, state)

# Обработка нажатия кнопки "Отмена"
@router.message(F.text == cancel_text)
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await start(message, state)

# Обработка нажатия кнопки "Добавить чек"
@router.callback_query(F.data == "send_screenshot", CryptoBuy.waiting_for_payment)
async def ask_for_screenshot(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Пожалуйста, отправьте скриншот оплаты:")
    await state.set_state(CryptoBuy.waiting_for_screenshot)

# Обработка нажатий кнопок о завершении заказа
@router.callback_query()
async def callback_check(callback: CallbackQuery, state: FSMContext):
    data = callback.data.split(':')
    if data[0] == 'cancel':
        if await state.get_state() == CryptoBuy.waiting_for_payment or await state.get_state() == CryptoBuy.waiting_for_screenshot:
            await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)
            await callback.message.answer('❌ Заказ успешно отменён!')
            await state.clear()
            active_deals.pop(callback.message.chat.id, None)
            await start(callback.message, state)
        else:
            await callback.message.answer('❌ Этот заказ уже завершён!')
            await state.clear()
            await start(callback.message, state)
            return

        for admin_id in admins:
            try:
                await callback.bot.send_message(admin_id, f'❌ Пользователь @{callback.message.chat.username or callback.message.chat.id} отменил заказ!\n\nID заказа: {data[1]}', parse_mode='HTML')
            except Exception as e:
                print(f"Не удалось отправить сообщение администратору {admin_id}: {e}")
    elif data[0] == 'cancel_deal':
        try:
            user_id = data[1]
            username = data[2]
            task = active_deals.get(int(user_id))

            if task:
                task.cancel()
                active_deals.pop(user_id, None)
                await callback.message.answer(f"✅ Сделка с пользователем @{username} завершена.")
                await callback.bot.send_message(user_id, '✅ <b>Администратор завершил сделку!</b>\n\n💵 Средства отправлены на указанный вами кошелёк', parse_mode='HTML')
                await state.clear()
                await start(callback.message, state)
            else:
                await callback.message.answer("❗ Сделка с этим пользователем уже завершена!", show_alert=True)
                await state.clear()
                await start(callback.message, state)
        except Exception:
            await callback.answer("⚠️ Ошибка", show_alert=True)

# Функция по запуску таймера в 15 минут
async def payment_timer(message: Message, state: FSMContext, bot, pay_id):
    await asyncio.sleep(900)

    # Функция для отправки сообщений админам
    async def message_for_admins():
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, f'❌ У пользователя @{message.chat.username or message.chat.id} истекло время на оплату.\n\nСделка завершена.\n<i>ID заказа:</i> <code>{pay_id}</code>', parse_mode='HTML')
            except Exception as e:
                print(f"Не удалось отправить сообщение администратору {admin_id}: {e}")

    if await state.get_state() == CryptoBuy.waiting_for_payment: # Завершаем сделку, если пользователь не успел произвести оплату.
        await bot.send_message(message.chat.id, f"⏳ Время на оплату истекло.\n\n<b>Сделка завершена.</b>\n<i>ID заказа:</i> <code>{pay_id}</code>", parse_mode='HTML')
        await state.clear()
        await message_for_admins()
    elif await state.get_state() == CryptoBuy.waiting_for_screenshot: # Если пользователь нажал на кнопку добавления чека, даём ему еще время.
        await asyncio.sleep(120)
        await bot.send_message(message.chat.id, f"⏳ Время на оплату истекло.\n\n<b>Сделка завершена.</b>\n<i>ID заказа:</i> <code>{pay_id}</code>", parse_mode='HTML')
        await state.clear()
        await message_for_admins()

    active_deals.pop(message.chat.id, None)