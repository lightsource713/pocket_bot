from cx_Freeze import setup, Executable

base = None    

executables = [Executable("trading_bot.py", base=base)]

packages = ["idna","threading","time","tkinter","selenium","datetime","base64","json","random","os","platform","stock_indicators"]
files = [("icon.png", "icon.png")]
options = {
    'build_exe': {    
        'packages':packages,
        'include_files': files,
    },    
}

setup(
    name = "TradingBot",
    options = options,
    version = "1.0.0",
    description = 'Pocket Option Platform Trading Bot',
    executables = executables
)