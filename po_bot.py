import base64
import json
import random
import time
from datetime import datetime, timedelta

import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import companies, get_driver

BASE_URL = 'https://pocketoption.com'
LENGTH_STACK_MIN = 460
LENGTH_STACK_MAX = 1000
PERIOD = 1
TIME = 1
SMA_LONG = 50
SMA_SHORT = 8
PERCENTAGE = 0.91
STACK = {}
ACTIONS = {}
MAX_ACTIONS = 1
ACTIONS_SECONDS = PERIOD - 1
LAST_REFRESH = datetime.now()
CURRENCY = None
CURRENCY_CHANGE = False
CURRENCY_CHANGE_DATE = datetime.now()
HISTORY_TAKEN = False
CLOSED_TRADES_LENGTH = 3
MODEL = None
SCALER = None
PREVIOUS = 1200
MAX_DEPOSIT = 0
MIN_DEPOSIT = 0
INIT_DEPOSIT = None
PREVIOUS_SPLIT=None
PREVIOUS_DEPOSIT=None
FIRST_BET = False

NUMBERS = {
    '0': '11',
    '1': '7',
    '2': '8',
    '3': '9',
    '4': '4',
    '5': '5',
    '6': '6',
    '7': '1',
    '8': '2',
    '9': '3',
}
IS_AMOUNT_SET = True
AMOUNTS = []
EARNINGS = 15
MARTINGALE_COEFFICIENT = 2.5
INIT_AMOUNT= 2
STEP=6

# Defined periods for Ichimoku elements
TENKAN_PERIOD = 1
KIJUN_PERIOD = 1
SENKOU_B_PERIOD = 52

driver = get_driver()

def load_web_driver():
    url = f'{BASE_URL}/en/cabinet/demo-quick-high-low/'
    driver.get(url)

def calculate_ichimoku_elements(closes):
    if len(closes) < max(TENKAN_PERIOD, KIJUN_PERIOD, SENKOU_B_PERIOD):
        return None, None, None, None, None
    
    # Calculate Tenkan-sen (Conversion Line)
    tenkan_sen = (max(closes[-TENKAN_PERIOD*15:]) + min(closes[-TENKAN_PERIOD*15:])) / 2
    
    # Calculate Kijun-sen (Base Line)
    kijun_sen = (max(closes[-KIJUN_PERIOD*15:]) + min(closes[-KIJUN_PERIOD*15:])) / 2
    
    # Calculate Senkou Span A (Leading Span A)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2)
    
    # Calculate Senkou Span B (Leading Span B)
    senkou_span_b = (max(closes[-SENKOU_B_PERIOD*15:]) + min(closes[-SENKOU_B_PERIOD*15:])) / 2
    
    # Calculate Chikou Span (Lagging Span)
    chikou_span = closes[-1]
    
    return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span

def wait_for_element(css_selector, timeout=5):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
    except Exception as e:
        print(f"Element not found: {css_selector}, Exception: {e}")
        return None

def do_action(signal):
    action = True
    try:
        last_value = list(STACK.values())[-1]
    except:
        return
    global ACTIONS, IS_AMOUNT_SET,PREVIOUS_DEPOSIT
    for dat in list(ACTIONS.keys()):
        if dat < datetime.now() - timedelta(seconds=ACTIONS_SECONDS):
            del ACTIONS[dat]

    if action:
        if len(ACTIONS) >= MAX_ACTIONS:
            action = False

    if action:
        if ACTIONS:
            if signal == 'call':
                action = False
            elif signal == 'put':
                action = False

    if action:
        try:
            print(f"Do Action:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {signal.upper()}, currency: {CURRENCY} last_value: {last_value}")
            action_button = wait_for_element(f'.btn-{signal}')
            if action_button:
                action_button.click()
                ACTIONS[datetime.now()] = last_value
                IS_AMOUNT_SET = False
                time.sleep(2)
                deposit = wait_for_element('body > div.wrapper > div.wrapper__top > header > div.right-block > div.right-block__item.js-drop-down-modal-open > div > div.balance-info-block__data > div.balance-info-block__balance > span')
                PREVIOUS_DEPOSIT = float(deposit.text)
        except Exception as e:
            print(e)

def hand_delay():
    time.sleep(random.choice([0.6]))

def get_amounts(amount):
    if amount > 1999:
        amount = 1999
    amounts = []
    index= 0 
    while index<STEP+1:
        if not INIT_AMOUNT:            
            amount = int(amount / MARTINGALE_COEFFICIENT)
            amounts.insert(0, amount)
            if amounts[0] <= 1:
                amounts[0] = 1
                return amounts
        else:
            amounts.append(int(INIT_AMOUNT*MARTINGALE_COEFFICIENT**index))
            index=index+1
    return amounts

def check_values(stack):
    try:
        deposit = wait_for_element('body > div.wrapper > div.wrapper__top > header > div.right-block > div.right-block__item.js-drop-down-modal-open > div > div.balance-info-block__data > div.balance-info-block__balance > span')
        if deposit is None:
            return
    except Exception as e:
        print(e)

    global IS_AMOUNT_SET, AMOUNTS, INIT_DEPOSIT,PREVIOUS_SPLIT,PREVIOUS_DEPOSIT,FIRST_BET

    if not INIT_DEPOSIT:
        INIT_DEPOSIT = float(deposit.text)

    if not AMOUNTS:
        AMOUNTS = get_amounts(float(deposit.text))

    if not IS_AMOUNT_SET:
        if ACTIONS and datetime.now().second % PERIOD != 0:
            return

        try:
            closed_tab = wait_for_element('#bar-chart > div > div > div.right-widget-container > div > div.widget-slot__header > div.divider > ul > li:nth-child(2) > a')
            if closed_tab is None:
                return
            closed_tab_parent = closed_tab.find_element(by=By.XPATH, value='..')
            if closed_tab_parent.get_attribute('class') == '':
                closed_tab_parent.click()
        except:
            pass
        hand_delay()
        closed_trades_currencies = driver.find_elements(by=By.CLASS_NAME, value='deals-list__item')
        if closed_trades_currencies:
            last_split = closed_trades_currencies[0].text.split('\n')
            current_deposit = wait_for_element('body > div.wrapper > div.wrapper__top > header > div.right-block > div.right-block__item.js-drop-down-modal-open > div > div.balance-info-block__data > div.balance-info-block__balance > span')
            # PREVIOUS_DEPOSIT = float(deposit.text)
            print("PREVIOUS_DEPOSIT:",PREVIOUS_DEPOSIT)
            print("current_deposit:",float(current_deposit.text))
            print("last_split:",last_split)
            print("prev_split:",PREVIOUS_SPLIT)
            # if not PREVIOUS_SPLIT == None :
            #     return
            if PREVIOUS_SPLIT == last_split and PREVIOUS_DEPOSIT==float(current_deposit.text):    
                print("SAME")
                return
            if len(last_split) < 5:  # Ensure last_split has expected elements
                return
            try:
                amount = wait_for_element('#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--bet-amount > div.block__control.control > div.control__value.value.value--several-items > div > input[type=text]')
                if amount is None:
                    return
                amount_value = int(amount.get_attribute('value')[1:])
                base = '#modal-root > div > div > div > div > div.trading-panel-modal__in > div.virtual-keyboard.js-virtual-keyboard > div > div:nth-child(%s) > div'
                if '$0' != last_split[4]:  # win
                    print("Win!!!")
                    if amount_value > 1:
                        amount.click()
                        # hand_delay()
                        for number in str(INIT_AMOUNT):
                            numeric_button = wait_for_element(base % NUMBERS[number])
                            if numeric_button:
                                numeric_button.click()
                        AMOUNTS = get_amounts(float(deposit.text))  # refresh amounts
                elif '$0' != last_split[3]:  # draw
                    print("Draw!!!")
                    pass
                else:  # lose
                    print("Lose!!!")
                    amount.click()
                    time.sleep(random.choice([0.6]))
                    if amount_value in AMOUNTS and AMOUNTS.index(amount_value) + 1 < len(AMOUNTS):
                        next_amount = AMOUNTS[AMOUNTS.index(amount_value) + 1]
                        print("next_amount:", next_amount)
                        for number in str(next_amount):
                            numeric_button = wait_for_element(base % NUMBERS[number])
                            if numeric_button:
                                numeric_button.click()
                                hand_delay()
                    else:  # reset to 1
                        for number in str(INIT_AMOUNT):
                            numeric_button = wait_for_element(base % NUMBERS[number])
                            if numeric_button:
                                numeric_button.click()
                                # hand_delay()
                closed_tab_parent.click()
            except Exception as e:
                print(e)
            PREVIOUS_SPLIT = last_split
        IS_AMOUNT_SET = True


    # if IS_AMOUNT_SET and datetime.now().second % PERIOD == 0:
    if IS_AMOUNT_SET:
        
        closes = list(stack.values())
        ichimoku_values = calculate_ichimoku_elements(closes)
        current_price = closes[-1]
        if not ichimoku_values:
            return

        tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span = ichimoku_values

        if senkou_span_a>chikou_span:
            do_action('put')
        else:
            do_action('call')

        if not FIRST_BET:
            FIRST_BET = True
            time.sleep(10)


def websocket_log(stack):
    global CURRENCY, CURRENCY_CHANGE, CURRENCY_CHANGE_DATE, LAST_REFRESH, HISTORY_TAKEN, MODEL, INIT_DEPOSIT
    try:
        current_symbol = driver.find_element(by=By.CLASS_NAME, value='current-symbol').text
        if current_symbol != CURRENCY:
            CURRENCY = current_symbol
            CURRENCY_CHANGE = True
            CURRENCY_CHANGE_DATE = datetime.now()
    except:
        pass

    if CURRENCY_CHANGE and CURRENCY_CHANGE_DATE < datetime.now() - timedelta(seconds=5):
        stack = {}  # drop stack when currency changed
        HISTORY_TAKEN = False  # take history again
        time.sleep(2)
        driver.refresh()
        CURRENCY_CHANGE = False
        MODEL = None
        INIT_DEPOSIT = None

    for wsData in driver.get_log('performance'):
        message = json.loads(wsData['message'])['message']
        response = message.get('params', {}).get('response', {})
        if response.get('opcode', 0) == 2 and not CURRENCY_CHANGE:
            payload_str = base64.b64decode(response['payloadData']).decode('utf-8')
            data = json.loads(payload_str)
            if not HISTORY_TAKEN:
                if 'history' in data:
                    stack = {int(d[0]): d[1] for d in data['history']}
                    print(f"History taken for asset: {data['asset']}, period: {data['period']}, len_history: {len(data['history'])}, len_stack: {len(stack)}")
            try:
                current_symbol = driver.find_element(by=By.CLASS_NAME, value='current-symbol').text
                symbol, timestamp, value = data[0]
            except:
                continue
            try:
                if current_symbol.replace('/', '').replace(' ', '') != symbol.replace('_', '').upper() and companies.get(current_symbol) != symbol:
                    continue
            except:
                pass

            if len(stack) == LENGTH_STACK_MAX:
                first_element = next(iter(stack))
                del stack[first_element]
            if len(stack) < LENGTH_STACK_MAX:
                if int(timestamp) in stack:
                    return stack
                else:
                    stack[int(timestamp)] = value
            elif len(stack) > LENGTH_STACK_MAX:
                stack = {}
            if len(stack) >= LENGTH_STACK_MIN:
                check_values(stack)
    return stack

load_web_driver()
while True:
    STACK = websocket_log(STACK)
