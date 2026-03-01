import pandas as pd
import datetime

# --- ENGINE INTERFACE ---

def build_base_calendar(year_min, year_max):
    """
    Layer A: Deterministic base calendar.
    Generates the skeleton with Year, Month, Day, Weekday.
    """
    dates = pd.date_range(start=f'{year_min}-01-01', end=f'{year_max}-12-31', freq='D')
    df = pd.DataFrame({'fecha': dates})
    
    # Basic Time Features
    df['año'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    df['dia'] = df['fecha'].dt.day
    df['weekday'] = df['fecha'].dt.weekday # 0=Mon, 6=Sun
    
    # Layer A Rules
    df['día par del mes'] = (df['dia'] % 2 == 0).astype(int)
    df['día impar del mes'] = (df['dia'] % 2 != 0).astype(int)
    df['fin de semana'] = df['weekday'].isin([5, 6]).astype(int)
    
    # Period Placeholders (can be expanded later)
    # df['inicio del trimestre 1']...
    
    return df

def run_recalculation_pipeline(df, event_configs):
    """
    Layer C: Derived Rules Pipeline.
    1. Reset derived columns.
    2. Compute Business Days (es_habil).
    3. Compute Offsets with Suppression.
    
    event_configs: dict or list of event definitions (names of columns in Layer B)
                   e.g. ['día festivo', 'día de pago']
    """
    # 1. Compute Business Days
    # Constraint: 'día festivo' and 'fin de semana' determine this.
    # We assume 'día festivo' is the primary "Holiday" event.
    # Other events might not be holidays (e.g. 'día de pago').
    
    if 'día festivo' in df.columns:
        df['es_habil'] = ((df['fin de semana'] == 0) & (df['día festivo'] == 0)).astype(int)
    else:
        # Fallback if no specific holiday column
        df['es_habil'] = (df['fin de semana'] == 0).astype(int)

    # 2. Compute Labor Rules (First/Last business day)
    # (Simplified for now, can be expanded to fill specific columns)
    
    # 3. Compute Offsets
    for event_cfg in event_configs:
        # event_cfg is dict: {'name': '...', 'offset_days': 10, ...}
        # OR string if legacy list passed (handle both for robustness)
        if isinstance(event_cfg, str):
             name = event_cfg
             N = 10
        else:
             name = event_cfg['name']
             N = event_cfg.get('offset_days', 10)
             
        if name in df.columns:
             # Apply offsets ±N days
             df = _apply_offsets(df, name, N=N)
             
    return df

def _apply_offsets(df, event_col, N=10):
    """
    Internal: Applies offsets with Suppression Rule.
    If target day is ALREADY the event, do not mark as offset.
    """
    # Helper to enforce column existence
    for k in range(1, N+1):
        pre_col = f'{k} días antes de {event_col}'
        post_col = f'{k} días después de {event_col}'
        if pre_col not in df.columns: df[pre_col] = 0
        if post_col not in df.columns: df[post_col] = 0
        
        # RESET before computing (important for recalculation)
        df[pre_col] = 0
        df[post_col] = 0

    # Get indices where event is active
    event_indices = df.index[df[event_col] == 1].tolist()
    
    dates = df['fecha'].dt.date.tolist()
    # Map date -> index for fast lookup
    date_to_idx = {d: i for i, d in enumerate(dates)}
    
    for idx in event_indices:
        base_date = dates[idx]
        
        for k in range(1, N+1):
            # Before
            target_date_pre = base_date - datetime.timedelta(days=k)
            t_idx_pre = date_to_idx.get(target_date_pre)
            
            if t_idx_pre is not None:
                # SUPPRESSION: If target is also 'event_col', skip
                if df.at[t_idx_pre, event_col] != 1:
                    col_name = f'{k} días antes de {event_col}'
                    df.at[t_idx_pre, col_name] = 1
            
            # After
            target_date_post = base_date + datetime.timedelta(days=k)
            t_idx_post = date_to_idx.get(target_date_post)
            
            if t_idx_post is not None:
                if df.at[t_idx_post, event_col] != 1:
                    col_name = f'{k} días después de {event_col}'
                    df.at[t_idx_post, col_name] = 1
                    
    return df
