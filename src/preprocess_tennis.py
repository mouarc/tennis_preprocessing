import pandas as pd
from src.config import (
    ATP_HISTORY,
)

matchs_of_day = "data/data_pred_before"

def concat_latest_history(latest_history: pd.DataFrame) -> pd.DataFrame:
    atp_history = pd.read_csv(ATP_HISTORY)
    df_history = pd.concat([atp_history, latest_history])
    return df_history
