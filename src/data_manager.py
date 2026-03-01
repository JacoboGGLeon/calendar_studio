import pandas as pd
import os
from datetime import date, timedelta

def generate_default_calendar(year=2026):
    """Generates a default daily calendar for the given year."""
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    delta = end_date - start_date
    
    dates = []
    for i in range(delta.days + 1):
        day = start_date + timedelta(days=i)
        dates.append(day)
        
    df = pd.DataFrame({'fecha': dates})
    df['fecha'] = pd.to_datetime(df['fecha'])
    
    # Add some basic default columns for demonstration
    df['dia festivo'] = 0
    df['fin de semana'] = df['fecha'].dt.dayofweek.apply(lambda x: 1 if x >= 5 else 0)
    df['nota'] = ""
    
    return df

def load_or_generate_data(file_path: str):
    """Loads calendar data from CSV or generates it if missing."""
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            # Ensure fecha is datetime
            if 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha'])
            return df
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return generate_default_calendar()
    else:
        print(f"File {file_path} not found. Generating default data.")
        return generate_default_calendar()

def save_data(df: pd.DataFrame, file_path: str):
    """Saves the dataframe to CSV."""
    df.to_csv(file_path, index=False)
