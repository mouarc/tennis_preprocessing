
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re
import argparse
from os import path, makedirs
import pandas as pd
from datetime import datetime, timedelta
from src.config import (
    URL, 
    PATH_DF_PRED_BEFORE,
    FORMAT_DATE,
    TODAY,
    TOMORROW,
)


def set_driver(url: str):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)
    except Exception as e:
        print(f"Error: Cannot open url: {url} {e}")
        driver.quit()
        exit()
    return driver  


def save_df_for_pred(df: pd.DataFrame, day: str, atp_or_wta: str):
    if day == "today":
        date_str = TODAY.strftime(FORMAT_DATE)
    else:
        date_str = TOMORROW.strftime(FORMAT_DATE)
    
    filename = f"{atp_or_wta.upper()}-{date_str}.csv"
    path_file = path.join(PATH_DF_PRED_BEFORE, filename)

    if not path.exists(PATH_DF_PRED_BEFORE):
        makedirs(PATH_DF_PRED_BEFORE, exist_ok=True)

    if path.exists(path_file):
        df_tmp = pd.read_csv(path_file)
    else:
        df_tmp = pd.DataFrame()

    df = pd.concat([df_tmp, df])
    df.drop_duplicates(keep="last", inplace=True)
    df.to_csv(path_file, index=False)
    