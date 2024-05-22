import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from os import path, makedirs
from datetime import datetime
from src.tennis_preprocessing.config import (
    URL_ATP_FILES,
    ATP_FILE_XPATH,
    ATP_FILES_DIR
)

def download_atp_file(year: int, data_dir: str = ATP_FILES_DIR):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL_ATP_FILES)
    wait = WebDriverWait(driver, 3)

    current_year = datetime.now().year
    suffix = current_year - year + 1

    if suffix < 1:
        print(f"No file found for the year {year}")
        driver.quit()
        return

    dynamic_xpath = f"{ATP_FILE_XPATH}a[{suffix}]"
    element = wait.until(EC.presence_of_element_located((By.XPATH, dynamic_xpath)))

    # Check if selected year is the expected one
    element_text = element.text
    if str(year) in element_text:
        file_url = element.get_attribute("href")
        file_name = path.join(data_dir, f"atp_{file_url.split('/')[-1]}")
        makedirs(data_dir, exist_ok=True)
        response = requests.get(file_url)
        with open(file_name, "wb") as file:
            file.write(response.content)
        print(f"Downloaded: {file_name}")
    else:
        print(f"No file found for the year {year}")

    driver.quit()
