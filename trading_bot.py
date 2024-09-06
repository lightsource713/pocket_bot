import threading
import time
from tkinter import Tk, Button, Label, Checkbutton, IntVar, StringVar, Entry, Frame, PhotoImage
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
from utils import companies, get_driver
import base64
import json
import random
import sys
import os

# Define your bot control variables
bot_running = False
bot_thread = None

BASE_URL = 'https://pocketoption.com/en/cabinet/demo-quick-high-low/'

LENGTH_STACK_MIN = 460
LENGTH_STACK_MAX = 1000
PERIOD = None
TIME = 1
SMA_LONG = 50
SMA_SHORT = 8
PERCENTAGE = 0.91
STACK = {}
ACTIONS = {}
MAX_ACTIONS = 1
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
TIME_FRAME = "00:00:10"

# Defined periods for Ichimoku elements
TENKAN_PERIOD = 1
KIJUN_PERIOD = 1
SENKOU_B_PERIOD = 52

driver = None

USE_MARTINGALE = True  # Flag to decide if Martingale is used


def load_web_driver():
    global driver
    driver = get_driver()
    url = f'{BASE_URL}'
    driver.get(url)

def calculate_ichimoku_elements(closes):
    global PERIOD
    if len(closes) < max(TENKAN_PERIOD, KIJUN_PERIOD, SENKOU_B_PERIOD):
        return None, None, None, None, None
    
    counts = int(1.5*PERIOD)
    
    # Calculate Tenkan-sen (Conversion Line)
    tenkan_sen = (max(closes[-(TENKAN_PERIOD*counts):]) + min(closes[-(TENKAN_PERIOD*counts):])) / 2
    
    # Calculate Kijun-sen (Base Line)
    kijun_sen = (max(closes[-KIJUN_PERIOD*counts:]) + min(closes[-KIJUN_PERIOD*counts:])) / 2
    
    # Calculate Senkou Span A (Leading Span A)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2)
    
    # Calculate Senkou Span B (Leading Span B)
    senkou_span_b = (max(closes[-SENKOU_B_PERIOD*counts:]) + min(closes[-SENKOU_B_PERIOD*counts:])) / 2
    
    # Calculate Chikou Span (Lagging Span)
    chikou_span = closes[-1]
    
    return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span

def wait_for_element(css_selector, timeout=5):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
    except Exception as e:
        return None

def do_action(signal):
    action = True
    try:
        last_value = list(STACK.values())[-1]
    except:
        return
    global ACTIONS, IS_AMOUNT_SET,PREVIOUS_DEPOSIT
    for dat in list(ACTIONS.keys()):
        if dat < datetime.now():
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
    time.sleep(random.choice([0.3, 0.4, 0.5]))

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
            if PREVIOUS_SPLIT == last_split and PREVIOUS_DEPOSIT==float(current_deposit.text):    
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
                    if amount_value > 1:
                        amount.click()
                        # hand_delay()
                        for number in str(INIT_AMOUNT):
                            numeric_button = wait_for_element(base % NUMBERS[number])
                            if numeric_button:
                                numeric_button.click()
                        AMOUNTS = get_amounts(float(deposit.text))  # refresh amounts
                elif '$0' != last_split[3]:  # draw
                    pass
                else:  # lose
                    amount.click()
                    time.sleep(random.choice([0.6]))
                    if amount_value in AMOUNTS and AMOUNTS.index(amount_value) + 1 < len(AMOUNTS):
                        next_amount = AMOUNTS[AMOUNTS.index(amount_value) + 1]
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

    if IS_AMOUNT_SET:
        closes = list(stack.values())
        ichimoku_values = calculate_ichimoku_elements(closes)
        current_price = closes[-1]
        if not ichimoku_values:
            return

        tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span = ichimoku_values
        if senkou_span_a > chikou_span:
            do_action('put')
        else:
            do_action('call')

        if not FIRST_BET:
            FIRST_BET = True
            time.sleep(PERIOD)

def setPeriod (times):
    global PERIOD
    hours = times[0]
    minutes = times[1]
    seconds = times[2]
    PERIOD = int(hours)*3600 + int(minutes)*60 + int(seconds)

def init_timeframe():
    try:
        timeDiv = wait_for_element('#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--expiration-inputs > div.block__control.control > div.control__value.value.value--several-items > div')

        if timeDiv is None:
            return
        
        timeDiv.click()
        hand_delay()

        plus_base = '#modal-root > div > div > div > div.trading-panel-modal__in > div:nth-child(%s) > a.btn-plus'
        minus_base = '#modal-root > div > div > div > div.trading-panel-modal__in > div:nth-child(%s) > a.btn-minus'
        
        current = timeDiv.text.split(":")
        target = TIME_FRAME.split(":")

        for i in range(3):
            plus_button = wait_for_element(plus_base % (i + 1))
            minus_button = wait_for_element(minus_base % (i + 1))

            diff = int(target[i]) - int(current[i])

            if i == 2 and target[0] == 0 and target[1] == 0: diff -= 5
            for j in range(abs(diff)):
                if diff < 0 : 
                    minus_button.click()
                    hand_delay()
                else:
                    plus_button.click()
                    hand_delay()
        
    except Exception as e:
        print(e)    

    time.sleep(1)

def init_amount():
    try:
        amount = wait_for_element('#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--bet-amount > div.block__control.control > div.control__value.value.value--several-items > div > input[type=text]')
        if amount is None:
            return
        amount.click()
        hand_delay()
        base = '#modal-root > div > div > div > div > div.trading-panel-modal__in > div.virtual-keyboard.js-virtual-keyboard > div > div:nth-child(%s) > div'
        for number in str(INIT_AMOUNT):
            numeric_button = wait_for_element(base % NUMBERS[number])
            if numeric_button:
                numeric_button.click()
                hand_delay()        
    except Exception as e:
        print(e)

    time.sleep(1)


def websocket_log(stack):
    global CURRENCY, CURRENCY_CHANGE, CURRENCY_CHANGE_DATE, LAST_REFRESH, HISTORY_TAKEN, MODEL, INIT_DEPOSIT,INIT_AMOUNT
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
        init_amount()
        init_timeframe()
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
            timeDiv = wait_for_element('#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--expiration-inputs > div.block__control.control > div.control__value.value.value--several-items > div')
            times = timeDiv.text.split(":")
            setPeriod(times)
            if not HISTORY_TAKEN:
                if 'history' in data:
                    stack = {int(d[0]): d[1] for d in data['history']}                    
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

def run_bot():
    global STACK

    init()
    load_web_driver()
    
    while bot_running:
        STACK = websocket_log(STACK)
        if not bot_running:
            break

    driver.quit()

def init():
    global INIT_AMOUNT, MARTINGALE_COEFFICIENT, TIME_FRAME, TENKAN_PERIOD, KIJUN_PERIOD, CURRENCY_CHANGE, CURRENCY_CHANGE_DATE
    INIT_AMOUNT = int(amount_var.get())
    MARTINGALE_COEFFICIENT = float(martingale_var.get())
    TIME_FRAME = time_var.get()
    TENKAN_PERIOD = int(tenkan_var.get())
    KIJUN_PERIOD = int(kijun_var.get())
    CURRENCY_CHANGE = True
    CURRENCY_CHANGE_DATE = datetime.now()

# Function to start the bot in a separate thread
def start_bot():
    global bot_running, bot_thread
    if not bot_running:
        bot_running = True
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.start()
        status_label.config(text="Bot Status: Running")
    else:
        status_label.config(text="Bot is already running")

# Function to stop the bot
def stop_bot():
    global bot_running
    if bot_running:
        bot_running = False
        if bot_thread:
            bot_thread.join()  # Wait for the thread to finish
        status_label.config(text="Bot Status: Stopped")
    else:
        status_label.config(text="Bot is already stopped")

# Function to toggle Martingale strategy
def toggle_demo():
    global BASE_URL
    if demo_toggle_var.get() == 1:
        BASE_URL = 'https://pocketoption.com/en/cabinet/demo-quick-high-low/'
    else:
        BASE_URL = 'https://pocketoption.com/en/cabinet/'

# Create the Tkinter UI
root = Tk()
root.title("Pocket Option Trading Bot")
root.geometry("500x400")
root.resizable(False, False)

# Check if the application is running as a frozen executable
if hasattr(sys, "_MEIPASS"):
    # Running from the .exe, access the bundled resource
    icon_path = os.path.join(sys._MEIPASS, "icon.png")
else:
    # Running from the Python script, use the normal path
    icon_path = "icon.png"  # Use relative path assuming the icon is in the same folder

# Load and set the icon
try:
    icon = PhotoImage(file=icon_path)
    root.wm_iconphoto(True, icon)
except Exception as e:
    print(f"Error loading icon: {e}")

# Create a status label to show whether the bot is running
title_label = Label(root, text="TRADING BOT CONTROL PANEL", font=("Helvetica", 20))
title_label.pack(pady=5)
status_label = Label(root, text="Click Start Bot to run the bot", font=("Helvetica", 12))
status_label.pack(pady=10)
# Create a frame for the input fields and labels
frame = Frame(root)
frame.pack(pady=20)

# Add the "Initial Amount" label and entry
amount_label = Label(frame, text="Initial Amount")
amount_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
amount_var = StringVar()
amount_var.set("1")
amount_entry = Entry(frame, width=20, textvariable=amount_var)
amount_entry.grid(row=1, column=1, padx=5, pady=5)

# Add the "Martingale Coefficent" label and entry
martingale_label = Label(frame, text="Martingale Coefficent")
martingale_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
martingale_var = StringVar()
martingale_var.set("2.5")
martingale_entry = Entry(frame, width=20, textvariable=martingale_var)
martingale_entry.grid(row=2, column=1, padx=5, pady=5)

# Add the "Time Frame" label and entry
time_label = Label(frame, text="Time Frame")
time_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")
time_var = StringVar()
time_var.set("00:00:10")
time_entry = Entry(frame, width=20, textvariable=time_var)
time_entry.grid(row=3, column=1, padx=5, pady=5)

# Add the "Tenkan Period" label and entry
tenkan_label = Label(frame, text="Tenkan Period")
tenkan_label.grid(row=4, column=0, padx=5, pady=5, sticky="e")
tenkan_var = StringVar()
tenkan_var.set("1")
tenkan_entry = Entry(frame, width=20, textvariable=tenkan_var)
tenkan_entry.grid(row=4, column=1, padx=5, pady=5)

# Add the "Kijun Period" label and entry
kijun_label = Label(frame, text="Kijun Period")
kijun_label.grid(row=5, column=0, padx=5, pady=5, sticky="e")
kijun_var = StringVar()
kijun_var.set("1")
kijun_entry = Entry(frame, width=20, textvariable=kijun_var)
kijun_entry.grid(row=5, column=1, padx=5, pady=5)

# Create the Martingale checkbox
demo_toggle_var = IntVar()
demo_toggle_var.set(1)
demo_checkbox = Checkbutton(root, text="Demo Money", variable=demo_toggle_var, command=toggle_demo)
demo_checkbox.pack(padx=5, pady=5)

# Button Frame
button_frame = Frame(root)
button_frame.pack(pady=20)

# Create the Start and Stop buttons
start_button = Button(button_frame, text="Start Bot", command=start_bot, width=20)
start_button.grid(row=0, column=0, padx=5, pady=5)

stop_button = Button(button_frame, text="Stop Bot", command=stop_bot, width=20)
stop_button.grid(row=0, column=1, padx=5, pady=5)

# Run the Tkinter event loop
root.mainloop()
