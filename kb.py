from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import uuid

cancel = '❌ Отмена'

commission_card = 18 # Комиссия для карт
commission_sbp = 13 # Комиссия для СБП

# Клавиатура с главным меню
start_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Купить BTC"),
            KeyboardButton(text="Купить USDT"),
            KeyboardButton(text="Купить LTC")
        ]], resize_keyboard=True)

# Кнопка "Отмена"
cancel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=cancel),
        ]], resize_keyboard=True)

# Кнопка выбора метода оплаты
payment_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=f"💳 Оплата картой СНГ ({commission_card}%)"),
            KeyboardButton(text=f"🏦 Оплата по СБП ({commission_sbp}%)")
        ],
        [
            KeyboardButton(text=cancel)
        ]
        ], resize_keyboard=True)

# Кнопка с пользовательским соглашением
user_agreement = InlineKeyboardMarkup(
    inline_keyboard=[
            [InlineKeyboardButton(text="📃 Пользовательское соглашение", url='https://telegra.ph/Polzovatelskoe-soglashenie-07-19-25')]
        ])

no_promocode_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text='🎟 Нет промокода.')
        ]
        ], resize_keyboard=True)

# Функция для получения кнопка с завершением сделки
def get_complete_btn(message):
    complete_btn = InlineKeyboardMarkup(
        inline_keyboard=[
                    [InlineKeyboardButton(
                        text="Завершить сделку",
                        callback_data=f"cancel_deal:{message.chat.id}:{message.chat.username or message.chat.id}"
                    )]
                ])
    return complete_btn

# Функция для получения текста, кнопок и ID заказа
def which_payment_method(amount, currency, cost, wallet, payment_method, promocode, discount, requisite):
    pay_id = str(uuid.uuid4())

    new_cost_card = (cost * (1 - discount / 100)) * (1 + commission_card / 100) if discount is not None else (cost + (cost / 100 * commission_card))
    new_cost_sbp = (cost * (1 - discount / 100)) * (1 + commission_sbp / 100) if discount is not None else (cost + (cost / 100 * commission_sbp))

    payment_method_is_card = (f"У вас есть 15 минут на оплату заказа!\n\n"
                              f"⚠️ <b>Отправляйте чётко ту сумму, которая указана в заказе, иначе Вы потеряете деньги!</b> ⚠️\n"
                              f"⚠️ <b>Переводы BTC на маленькую сумму могут задерживаться до 24 часов! (в среднем на 3-4 часа)</b>⚠️\n\n"
                              f"Вы покупаете {amount:.8f} {currency}\n"
                              f"К оплате: <code>{new_cost_card:.2f}</code> рублей.\n"
                              f"Адрес для получения: <code>{wallet}</code>\n"
                              f"Комиссия составляет {commission_card}%\n"
                              f"Промокод: {promocode if promocode else 'Нет'}\n\n"
                              f"СНГ карты Сбер, ТБанк, ВТБ.\n"
                              f"Реквизиты для оплаты: <code>{requisite}</code>\n\n"
                              f"<i>ID заказа: <code>{pay_id}</code></i>")

    payment_method_is_sbp = (f"У вас есть <b>15 минут</b> на оплату заказа!\n\n"
                             f"⚠️ <b>Отправляйте чётко ту сумму, которая указана в заказе, иначе Вы потеряете деньги!</b> ⚠️\n"
                             f"⚠️ <b>Переводы BTC на маленькую сумму могут задерживаться до 24 часов! (в среднем на 3-4 часа)</b>⚠️\n\n"
                             f"Вы покупаете {amount:.8f} {currency}\n"
                             f"К оплате: <code>{new_cost_sbp:.2f}</code> рублей.\n"
                             f"Адрес для получения: <code>{wallet}</code>\n"
                             f"Комиссия составляет {commission_sbp}% + 5% комиссия сервиса\n"
                             f"Промокод: {promocode}\n\n"
                             f"Чтобы оплатить, нажмите на кнопку ниже, выберите точную сумму к оплате и нажмите кнопку \"СБП\"\n\n"
                             f"<i>ID заказа: <code>{pay_id}</code></i>")

    if payment_method == f"💳 Оплата картой СНГ ({commission_card}%)":
        screenshot_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧾 Добавить чек", callback_data="send_screenshot")],
            [InlineKeyboardButton(text="🚫 Отменить заказ", callback_data=f'cancel:{pay_id}')]
        ])
        return payment_method_is_card, screenshot_kb, pay_id, new_cost_card
    elif payment_method == f"🏦 Оплата по СБП ({commission_sbp}%)":
        sbp = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💵 Оплатить по СБП", url='https://tips.tips/000000718')],
            [InlineKeyboardButton(text="🧾 Добавить чек", callback_data='send_screenshot')],
            [InlineKeyboardButton(text="🚫 Отменить заказ", callback_data=f'cancel:{pay_id}')]
        ])
        return payment_method_is_sbp, sbp, pay_id, new_cost_sbp
