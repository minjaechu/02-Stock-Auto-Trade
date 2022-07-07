import requests
import json
import datetime
from pytz import timezone
import time
import yaml

with open('config.yaml', encoding='UTF-8') as f:
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
APP_KEY = _cfg['APP_KEY']
APP_SECRET = _cfg['APP_SECRET']
ACCESS_TOKEN = ""
CANO = _cfg['CANO']
ACNT_PRDT_CD = _cfg['ACNT_PRDT_CD']
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']
URL_BASE = _cfg['URL_BASE']

def send_message(msg):
    """Discordメッセージ転送"""
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
    requests.post(DISCORD_WEBHOOK_URL, data=message)
    print(message)

def get_access_token():
    """トークン発行"""
    headers = {"content-type":"application/json"}
    body = {"grant_type":"client_credentials",
    "appkey":APP_KEY, 
    "appsecret":APP_SECRET}
    PATH = "oauth2/tokenP"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    ACCESS_TOKEN = res.json()["access_token"]
    return ACCESS_TOKEN
    
def hashkey(datas):
    """暗号化"""
    PATH = "uapi/hashkey"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
    'content-Type' : 'application/json',
    'appKey' : APP_KEY,
    'appSecret' : APP_SECRET,
    }
    res = requests.post(URL, headers=headers, data=json.dumps(datas))
    hashkey = res.json()["HASH"]
    return hashkey

def get_current_price(market="NAS", code="AAPL"):
    """現在値照会"""
    PATH = "uapi/overseas-price/v1/quotations/price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appKey":APP_KEY,
            "appSecret":APP_SECRET,
            "tr_id":"HHDFS00000300"}
    params = {
        "AUTH": "",
        "EXCD":market,
        "SYMB":code,
    }
    res = requests.get(URL, headers=headers, params=params)
    return float(res.json()['output']['last'])

def get_target_price(market="NAS", code="AAPL"):
    """短期売買法で買収目標値照会"""
    PATH = "uapi/overseas-price/v1/quotations/dailyprice"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"HHDFS76240000"}
    params = {
        "AUTH":"",
        "EXCD":market,
        "SYMB":code,
        "GUBN":"0",
        "BYMD":"",
        "MODP":"0"
    }
    res = requests.get(URL, headers=headers, params=params)
    stck_oprc = float(res.json()['output2'][0]['open']) #当日時価
    stck_hgpr = float(res.json()['output2'][1]['high']) #前日ピーク
    stck_lwpr = float(res.json()['output2'][1]['low']) #前日低価
    target_price = stck_oprc + (stck_hgpr - stck_lwpr) * 0.5
    return target_price

def get_stock_balance():
    """株式残高照会"""
    PATH = "uapi/overseas-stock/v1/trading/inquire-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"JTTT3012R",
        "custtype":"P"
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }
    res = requests.get(URL, headers=headers, params=params)
    stock_list = res.json()['output1']
    evaluation = res.json()['output2']
    stock_dict = {}
    send_message(f"====株式保有残高====")
    for stock in stock_list:
        if int(stock['ovrs_cblc_qty']) > 0:
            stock_dict[stock['ovrs_pdno']] = stock['ovrs_cblc_qty']
            send_message(f"{stock['ovrs_item_name']}({stock['ovrs_pdno']}): {stock['ovrs_cblc_qty']}株")
            time.sleep(0.1)
    send_message(f"株式評価金額: ${evaluation['tot_evlu_pfls_amt']}")
    time.sleep(0.1)
    send_message(f"評価損益合計: ${evaluation['ovrs_tot_pfls']}")
    time.sleep(0.1)
    send_message(f"=================")
    return stock_dict

def get_balance():
    """현금 잔고조회"""
    PATH = "uapi/domestic-stock/v1/trading/inquire-psbl-order"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTC8908R",
        "custtype":"P",
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": "005930",
        "ORD_UNPR": "65500",
        "ORD_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "Y",
        "OVRS_ICLD_YN": "Y"
    }
    res = requests.get(URL, headers=headers, params=params)
    cash = res.json()['output']['ord_psbl_cash']
    send_message(f"注文可能現金残高: {cash}ウォン")
    return int(cash)

def buy(market="NASD", code="AAPL", qty="1", price="0"):
    """米国株式指定価買収"""
    PATH = "uapi/overseas-stock/v1/trading/order"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "OVRS_EXCG_CD": market,
        "PDNO": code,
        "ORD_DVSN": "00",
        "ORD_QTY": str(int(qty)),
        "OVRS_ORD_UNPR": f"{round(price,2)}",
        "ORD_SVR_DVSN_CD": "0"
    }
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"JTTT1002U",
        "custtype":"P",
        "hashkey" : hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    if res.json()['rt_cd'] == '0':
        send_message(f"[買収成功]{str(res.json())}")
        return True
    else:
        send_message(f"[買収失敗]{str(res.json())}")
        return False

def sell(market="NASD", code="AAPL", qty="1", price="0"):
    """米国株式指定価売却"""
    PATH = "uapi/overseas-stock/v1/trading/order"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "OVRS_EXCG_CD": market,
        "PDNO": code,
        "ORD_DVSN": "00",
        "ORD_QTY": str(int(qty)),
        "OVRS_ORD_UNPR": f"{round(price,2)}",
        "ORD_SVR_DVSN_CD": "0"
    }
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"JTTT1006U",
        "custtype":"P",
        "hashkey" : hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    if res.json()['rt_cd'] == '0':
        send_message(f"[売却成功]{str(res.json())}")
        return True
    else:
        send_message(f"[売却失敗]{str(res.json())}")
        return False

def get_exchange_rate():
    """환율 조회"""
    PATH = "uapi/overseas-stock/v1/trading/inquire-present-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appKey":APP_KEY,
            "appSecret":APP_SECRET,
            "tr_id":"CTRP6504R"}
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "OVRS_EXCG_CD": "NASD",
        "WCRC_FRCR_DVSN_CD": "01",
        "NATN_CD": "840",
        "TR_MKET_CD": "01",
        "INQR_DVSN_CD": "00"
    }
    res = requests.get(URL, headers=headers, params=params)
    exchange_rate = 1270.0
    if len(res.json()['output2']) > 0:
        exchange_rate = float(res.json()['output2'][0]['frst_bltn_exrt'])
    return exchange_rate

# 自動売買開始
try:
    ACCESS_TOKEN = get_access_token()

    nasd_symbol_list = ["AAPL"] # 買収希望種目リスト (NASD)
    nyse_symbol_list = ["KO"] # 買収希望種目リスト (NYSE)
    amex_symbol_list = ["LIT"] # 買収希望種目リスト (AMEX)
    symbol_list = nasd_symbol_list + nyse_symbol_list + amex_symbol_list
    bought_list = [] # 買収完了種目リスト
    total_cash = get_balance() # 保有現金照会
    exchange_rate = get_exchange_rate() # 為替照会
    stock_dict = get_stock_balance() # 保有株式照会
    for sym in stock_dict.keys():
        bought_list.append(sym)
    target_buy_count = 3 # 買収する種目数
    buy_percent = 0.33 # 種目ごとの買収金額割合
    buy_amount = total_cash * buy_percent / exchange_rate # 種目別注文金額計算(ドル)
    soldout = False

    send_message("===海外株式自動売買プログラムを始めます。===")
    while True:
        t_now = datetime.datetime.now(timezone('America/New_York')) # ニューヨーク基準現在時刻
        t_9 = t_now.replace(hour=9, minute=30, second=0, microsecond=0)
        t_start = t_now.replace(hour=9, minute=35, second=0, microsecond=0)
        t_sell = t_now.replace(hour=15, minute=45, second=0, microsecond=0)
        t_exit = t_now.replace(hour=15, minute=50, second=0,microsecond=0)
        today = t_now.weekday()
        if today == 5 or today == 6:  # 土曜または日曜の場合自動シャットダウン
            send_message("休日のため、プログラムを終了します。")
            break
        if t_9 < t_now < t_start and soldout == False: # 残余数量売却
            for sym, qty in stock_dict.items():
                market1 = "NASD"
                market2 = "NAS"
                if sym in nyse_symbol_list:
                    market1 = "NYSE"
                    market2 = "NYS"
                if sym in amex_symbol_list:
                    market1 = "AMEX"
                    market2 = "AMS"
                sell(market=market1, code=sym, qty=qty, price=get_current_price(market=market2, code=sym))
            soldout == True
            bought_list = []
            time.sleep(1)
            stock_dict = get_stock_balance()
        if t_start < t_now < t_sell :  # AM 09:35 ~ PM 03:45 : 買収
            for sym in symbol_list:
                if len(bought_list) < target_buy_count:
                    if sym in bought_list:
                        continue
                    market1 = "NASD"
                    market2 = "NAS"
                    if sym in nyse_symbol_list:
                        market1 = "NYSE"
                        market2 = "NYS"
                    if sym in amex_symbol_list:
                        market1 = "AMEX"
                        market2 = "AMS"
                    target_price = get_target_price(market2, sym)
                    current_price = get_current_price(market2, sym)
                    if target_price < current_price:
                        buy_qty = 0  # 買収数量初期化
                        buy_qty = int(buy_amount // current_price)
                        if buy_qty > 0:
                            send_message(f"{sym} 目標が達成({target_price} < {current_price}) 売却を行います。")
                            market = "NASD"
                            if sym in nyse_symbol_list:
                                market = "NYSE"
                            if sym in amex_symbol_list:
                                market = "AMEX"
                            result = buy(market=market1, code=sym, qty=buy_qty, price=get_current_price(market=market2, code=sym))
                            time.sleep(1)
                            if result:
                                soldout = False
                                bought_list.append(sym)
                                get_stock_balance()
                    time.sleep(1)
            time.sleep(1)
            if t_now.minute == 30 and t_now.second <= 5: 
                get_stock_balance()
                time.sleep(5)
        if t_sell < t_now < t_exit:  # PM 03:45 ~ PM 03:50 : 一括売却
            if soldout == False:
                stock_dict = get_stock_balance()
                for sym, qty in stock_dict.items():
                    market1 = "NASD"
                    market2 = "NAS"
                    if sym in nyse_symbol_list:
                        market1 = "NYSE"
                        market2 = "NYS"
                    if sym in amex_symbol_list:
                        market1 = "AMEX"
                        market2 = "AMS"
                    sell(market=market1, code=sym, qty=qty, price=get_current_price(market=market2, code=sym))
                soldout = True
                bought_list = []
                time.sleep(1)
        if t_exit < t_now:  # PM 03:50 ~ :プログラム終了
            send_message("プログラムを終了します")
            break
except Exception as e:
    send_message(f"[エラー]{e}")
    time.sleep(1)