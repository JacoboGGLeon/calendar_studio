import pandas as pd
import json
import os
import shutil

DATA_FILE = "calendario_2026.csv" # Hardcoded for now as per requirements, could be dynamic
META_FILE = "src/calendar_meta.json"

DEFAULT_META = {
    "events": [
        {"name": "día festivo", "color": "#E74C3C", "enabled": True, "offset_days": 10, "symbol": "🟥"},
        {"name": "día de pago de impuestos", "color": "#F39C12", "enabled": True, "offset_days": 5, "symbol": "🟧"},
        {"name": "día de cobro de quincena", "color": "#2ECC71", "enabled": True, "offset_days": 3, "symbol": "🟩"}
    ],
    "year_min": 2022,
    "year_max": 2027
}

def load_data(path=DATA_FILE):
    """
    Loads the calendar CSV. 
    Returns: DataFrame or None if not exists.
    """
    if not os.path.exists(path):
        return None
    try:
        # Try default encoding, then latin1
        df = pd.read_csv(path)
    except:
        df = pd.read_csv(path, encoding='latin1')
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'])
        
    # NORMALIZE COLUMNS (Encoding fixes)
    # Fix 'año' which might be read as 'ao' or 'aÃ±o'
    for c in df.columns:
        if 'a' in c and 'o' in c and len(c) <= 4 and c not in ['año', 'alto', 'bajo']:
             # Heuristic for mangled 'año'
             if c.startswith('a') and c.endswith('o'):
                 df.rename(columns={c: 'año'}, inplace=True)
                 
    # Ensure standard names exist if we loaded a legacy CSV or similar
    if 'año' not in df.columns and 'fecha' in df.columns:
        df['año'] = df['fecha'].dt.year
    if 'mes' not in df.columns and 'fecha' in df.columns:
        df['mes'] = df['fecha'].dt.month
    if 'dia' not in df.columns and 'fecha' in df.columns:
        df['dia'] = df['fecha'].dt.day
    if 'weekday' not in df.columns and 'fecha' in df.columns:
        df['weekday'] = df['fecha'].dt.weekday
        
    return df

def save_data_atomic(df, path=DATA_FILE):
    """
    Saves DataFrame to CSV atomically (write temp -> rename).
    """
    temp_path = path + ".tmp"
    try:
        # Use utf-8-sig for Excel compatibility in Spanish
        df.to_csv(temp_path, index=False, encoding='utf-8-sig')
        
        # Atomic Replace
        if os.path.exists(path):
            os.replace(temp_path, path)
        else:
            os.rename(temp_path, path)
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False

def load_meta(path=META_FILE):
    """
    Loads metadata (event definitions).
    """
    if not os.path.exists(path):
        save_meta(DEFAULT_META, path)
        return DEFAULT_META
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_meta(data, path=META_FILE):
    """
    Saves metadata.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
