import requests

# Функция для получения цены BTC в USDT
def get_price_btc():
    url = "https://api.rapira.net/open/market/rates"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    btc_usdt = None
    usdt_rub = None

    for item in data["data"]:
        if item["symbol"] == "BTC/USDT":
            btc_usdt = float(item["close"])
        elif item["symbol"] == "USDT/RUB":
            usdt_rub = float(item["close"])

    if btc_usdt is None or usdt_rub is None:
        raise Exception("Не удалось найти нужные курсы")

    btc_rub = btc_usdt * usdt_rub
    return btc_rub

# Функция для получения цены UDST в рублях
def get_price_usdt():
    url = "https://api.rapira.net/open/market/rates"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    usdt_rub = None

    for item in data["data"]:
        if item["symbol"] == "USDT/RUB":
            usdt_rub = float(item["close"])

    if usdt_rub is None:
        raise Exception("Не удалось найти нужные курсы")

    return usdt_rub

# Функция для получения цены LTC в USDT
def get_price_ltc():
    url = "https://api.rapira.net/open/market/rates"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    ltc_usdt = None
    usdt_rub = None

    for item in data["data"]:
        if item["symbol"] == "BTC/USDT":
            ltc_usdt = float(item["close"])
        elif item["symbol"] == "USDT/RUB":
            usdt_rub = float(item["close"])

    if ltc_usdt is None or usdt_rub is None:
        raise Exception("Не удалось найти нужные курсы")

    ltc_rub = ltc_usdt * usdt_rub
    return ltc_rub