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
from src.utils import (
    set_driver,
    save_df_for_pred,
)
from src.config import (
    URL, 
    PREFIX_MATCH_ID,
    URL_MATCH_PREFIX,
    URL_MATCH_SUFFIX,
    MAPPING_SURFACE,
    MAPPING_TOURNAMENT,
    MAPPING_LOCATION_SERIES_ATP,
    MAPPING_LOCATION_SERIES_WTA,
    PATH_DF_PRED_BEFORE,
    MAPPING_ROUNDS_INF_1000,
    MAPPING_ROUNDS_SUP_1000,
    INVALID_STATUS,
    BUTTON_NEXT_DAY,
    DATE_NEXT_DAY,
    )

# format_date = "%Y-%m-%d"
# today = datetime.now()
# tomorrow = today + timedelta(days=1)

# def set_driver() -> webdriver.chrome.webdriver.WebDriver:
#     chrome_options = Options()
#     chrome_options.add_argument("--no-sandbox")
#     chrome_options.add_argument("--headless")
#     chrome_options.add_argument("--disable-gpu")

#     driver = webdriver.Chrome(options=chrome_options)
#     try:
#         driver.get(URL)
#     except Exception as e:
#         print(f"Error: Cannot open url: {URL} {e}")
#         driver.quit()
#         exit()
#     return driver    

def get_ids_match(soup):
    div=soup.find_all("div", {"class":"event__match event__match--withRowLink event__match--scheduled event__match--twoLine"})
    # récupération des id de chaque match, servant à construire l'url
    ids_match = []
    for match in div:
        ids_match.append(match.get("id"))
    return ids_match
    
def get_today_html_content(driver):
    # récupération du contenu de la page
    # chrome_options = Options()
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--disable-gpu")

    # driver = webdriver.Chrome(options=chrome_options)
    # try:
    #     driver.get(URL)
    # except Exception as e:
    #     print(f"Error: Can't open url: {URL} {e}")
    #     driver.quit()
    #     exit()
    today_content = driver.page_source
    try:
        soup = BeautifulSoup(today_content, "html.parser")
    except Exception as e:
        print(f"Error: Cannot create soup object: {e}")
        driver.quit()
        exit()
    driver.quit()

    return soup

def get_next_day_html_content(driver):
    next_day = driver.find_element(By.XPATH, BUTTON_NEXT_DAY)
    driver.execute_script("arguments[0].click();", next_day)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.XPATH, DATE_NEXT_DAY)))
    next_day_content = driver.page_source
    try:
        soup = BeautifulSoup(next_day_content, "html.parser")
    except Exception as e:
        print(f"Error: Can't create soup object: {e}")
        driver.quit()
        exit()
    driver.quit()
    return soup
        
    
def parse_match_page(url):
    """Scrape a tennis match webpage and return html content

    Args:
        url (str): Link to the match webpage

    Returns:
        soup_match: BeautifoulSoup html content
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
    except Exception as e:
        print(f"Error: Can't open url: {url} {str(e)}")
        driver.quit()
        exit()
    
    driver.implicitly_wait(5)    
    page_content = driver.page_source
    try:
        soup_match = BeautifulSoup(page_content, "html.parser")
    except Exception as e:
        print(f"Error: Can't create soup object: {str(e)}")
        driver.quit()
        exit()
    driver.quit()
    return soup_match

pattern = re.compile(r'ATP - SIMPLES|WTA - SIMPLES')

def check_atp_wta(text: str):
    return bool(pattern.search(text))

def extract_rank(text):
    rank = re.search(r'\d+', text)
    if rank:
        return int(rank.group())
    else:
        return None

def check_match_status(content):
    try:
        status = content.find_all("span", {"class":"fixedHeaderDuel__detailStatus"})[0].text
    except AttributeError:
        status = ""
    except IndexError:
        status = ""
    return status

def parse_title(title):
    """Parse a string to find Serie, city, surface of the match and round

    Args:
        title (str): Description given when parsing the match page

    Returns:
        serie, city, surface, round: str
    """
    try:
        serie = title.split(" - ")[0]
        city = re.search(r':\s(.*?)(?:\s*\()', title)
        if city:
            city = city.group(1)
        surface = title.split(",")[-1].strip().split(" ")[0]
        round = re.search(r'\s-\s(.*?-\s(.*?))$', title)
        if round:
            round = round.group(2)
    except AttributeError:
        print(f"Impossible to parse title: {title}")
    return serie, city, surface, round

def mapping_round(series_value: str, round_value: str):
    """Apply a mapping on rounds to translate from fr. to en. depending of series
    
    Args:
        series_value (str): Rank tournament (eg: ATP250, ATP500)
        round_value (str): Round in the tournament

    Returns:
        round: str
    """
    if series_value in ["ATP250", "ATP500"]:
        return MAPPING_ROUNDS_INF_1000.get(round_value, round_value)
    else:
        return MAPPING_ROUNDS_SUP_1000.get(round_value, round_value)

def prepare_dataset_for_pred(df: pd.DataFrame, atp_or_wta: str):
    df["Tournament"] = df["Tournament"].map(MAPPING_TOURNAMENT)
    df["Surface"] = df["Surface"].map(MAPPING_SURFACE)
    if atp_or_wta.lower() == "atp":
        df["Series"] = df["Location"].map(MAPPING_LOCATION_SERIES_ATP)
    else:
        df["Series"] = df["Location"].map(MAPPING_LOCATION_SERIES_WTA)
    df["Round"] = df.apply(lambda row: mapping_round(row["Series"], row["Round"]), axis=1)
    df["GapRank"] = abs(df["Rank1"] - df["Rank2"])
    df["GapOdd"] = round(abs(df["Cote1"] - df["Cote2"]),2)
    df["SumRank"] = df["Rank1"] + df["Rank2"]
    df["SumOdd"] = round(df["Cote1"] + df["Cote2"], 2)
    
    return df

# def save_df_for_pred(df: pd.DataFrame, day: str, atp_or_wta: str):
#     if day == "today":
#         date_str = today.strftime(format_date)
#     else:
#         date_str = tomorrow.strftime(format_date)
    
#     filename = f"{atp_or_wta.upper()}-{date_str}.csv"
#     path_file = path.join(PATH_DF_PRED_BEFORE, filename)

#     if not path.exists(PATH_DF_PRED_BEFORE):
#         makedirs(PATH_DF_PRED_BEFORE, exist_ok=True)

#     if path.exists(path_file):
#         df_tmp = pd.read_csv(path_file)
#     else:
#         df_tmp = pd.DataFrame()

#     df = pd.concat([df_tmp, df])
#     df.drop_duplicates(keep="last", inplace=True)
#     df.to_csv(path_file, index=False)
    
def get_datas_per_match(ids_match):
    player1 = []
    player2 = []
    rank1 = []
    rank2 = []
    date = []
    cote1 = []
    cote2 = []
    city = []
    surface = []
    serie = []
    round = []
    court = [] # outdoor/indoor

    for id in ids_match:
        id_clean = id.split(PREFIX_MATCH_ID)[-1]
        url_match = f"{URL_MATCH_PREFIX}{id_clean}{URL_MATCH_SUFFIX}"
        print(url_match)
        content = parse_match_page(url_match)
        status = check_match_status(content)
        if any(inval_status in status for inval_status in INVALID_STATUS):
            continue
        else:
            title = content.find_all("span", {"class" : "tournamentHeader__country"})[0].text
            if check_atp_wta(title):
                try:
                    cotes = content.find_all("span", {"class":"oddsValueInner"})
                    cote1.append(float(cotes[-2].text))
                    cote2.append(float(cotes[-1].text))
                    serie0, city0, surface0, round0 = parse_title(title)
                    city.append(city0)
                    surface.append(surface0)
                    serie.append(serie0)
                    round.append(round0)
                    court.append("Outdoor")
                
                    players = content.find_all("div", {"class" : "participant__participantNameWrapper"})
                    player1.append(players[0].text)
                    player2.append(players[-1].text)
                    
                    ranks = content.find_all("div", {"class":"participant__participantRank"})
                    rank1.append(extract_rank(ranks[0].text))
                    rank2.append(extract_rank(ranks[-1].text))
                    
                    date_start = content.find("div", {"class":"duelParticipant__startTime"})
                    if date_start:
                        date_start = date_start.text
                        date_start = pd.to_datetime(date_start, format='%d.%m.%Y %H:%M').normalize()
                    date.append(date_start)
                    print(f"Match {url_match} OK.")
                except IndexError:
                    print(f"Not enough data for this match : {url_match}")
                    continue
            else:
                continue
    df_tmp = pd.DataFrame({
        "Player1": player1,
        "Player2": player2,
        "Date": date,
        "Location": city,
        "Tournament": city,
        "ATP or WTA": serie,
        "Court": court,
        "Surface": surface,
        "Round": round,
        "Rank1": rank1,
        "Rank2": rank2,
        "Cote1": cote1,
        "Cote2": cote2,
        })

    df_atp = df_tmp[df_tmp["ATP or WTA"]=="ATP"]
    df_wta = df_tmp[df_tmp["ATP or WTA"]=="WTA"]

    return df_atp, df_wta

def main():
    parser = argparse.ArgumentParser(description="Scrape any useful information for tennis matches from www.flashscore.fr")
    parser.add_argument("-t", "--tomorrow", action="store_true", help="Scrape data for the next day")
    args = parser.parse_args()
    driver = set_driver(url = URL)
    if args.tomorrow:
        day = "tomorrow"
        soup = get_next_day_html_content(driver)
    else:
        day = "today"
        soup = get_today_html_content(driver)

    ids = get_ids_match(soup)
    df_atp, df_wta = get_datas_per_match(ids)
    df_atp = prepare_dataset_for_pred(df_atp, atp_or_wta="atp")
    df_wta = prepare_dataset_for_pred(df_atp, atp_or_wta="wta")
    save_df_for_pred(df_atp, day, "atp")
    save_df_for_pred(df_wta, day, "wta")
    print(f"{len(df_atp) + len(df_wta)} matchs found.")
    
    
if __name__ == "__main__":
    main()
