import pandas as pd
import numpy as np
import datetime

# --- ENGINE LOGIC (from apoyo.md) ---

def build_base_calendar(year_min, year_max):
    """Layer A: Deterministic base calendar"""
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
    
    # Period logic (bi/tri/cuatri/semestre/annual)
    # Note: CSV has specifically 'inicio del trimestre 1', etc.
    # We will implement generic period logic if needed, but primarily 
    # we want to test the 'Derived Rules' (Layer C) which is the complex part.
    return df

def compute_business_days(df, events_list):
    """Layer C1: Business Days"""
    # Is Holiday if ANY event in events_list is present
    # In the specific schema of calendario_2026.csv, 'dia festivo' is explicit column
    # If we treat 'dia festivo' as Layer B (Input), we just use it.
    
    # es_habil logic
    is_weekend = df['fin de semana'] == 1
    # Assuming 'dia festivo' is already populated in Layer B
    is_holiday = df['da festivo'] == 1 # Note: weird encoding in CSV column name likely 'día festivo'
    
    # In the provided CSV dump, it looks like 'da festivo' might be the column. 
    # Using 'dia festivo' logic from CSV structure.
    
    df['es_habil'] = (~is_weekend & ~is_holiday).astype(int)
    return df

def apply_offsets(df, event_col, N=10):
    """Layer C3: Offsets"""
    # For every day where event_col == 1, mark neighbors
    
    # Get indices where event is active
    event_indices = df.index[df[event_col] == 1].tolist()
    
    # Create columns if not exist
    for k in range(1, N+1):
        pre_col = f'{k} das antes de {event_col}' # Matching CSV encoding likely
        post_col = f'{k} das despus de {event_col}'
        if pre_col not in df.columns: df[pre_col] = 0
        if post_col not in df.columns: df[post_col] = 0
    
    # Apply
    # Using simple loop for clarity/correctness over vectorization for the MVP verification
    dates = df['fecha'].dt.date.tolist()
    date_to_idx = {d: i for i, d in enumerate(dates)}
    
    for idx in event_indices:
        base_date = dates[idx]
        
        for k in range(1, N+1):
            # Before
            target_date = base_date - datetime.timedelta(days=k)
            t_idx = date_to_idx.get(target_date)
            if t_idx is not None:
                # SUPPRESSION RULE: If the offset day is ITSELF a holiday, don't mark it?
                # or if df.at[t_idx, event_col] == 1?
                if df.at[t_idx, event_col] != 1:
                    pre_col = f'{k} das antes de {event_col}'
                    df.at[t_idx, pre_col] = 1
                
            # After
            target_date = base_date + datetime.timedelta(days=k)
            t_idx = date_to_idx.get(target_date)
            if t_idx is not None:
                if df.at[t_idx, event_col] != 1:
                    post_col = f'{k} das despus de {event_col}'
                    df.at[t_idx, post_col] = 1
                
    return df

# --- VERIFICATION SCRIPT ---

def verify_logic():
    print("Starting Logic Verification...")
    
    # 1. Load Ground Truth
    try:
        if 'calendario_2026.csv' not in pd.read_csv('calendario_2026.csv').columns:
            # Handle encoding or path
            GT = pd.read_csv('calendario_2026.csv', encoding='latin1') # common for Spanish
        else:
            GT = pd.read_csv('calendario_2026.csv')
    except Exception as e:
        print(f"Failed to load CSV: {e}")
        # Try default UTF-8 if latin1 failed or vice versa
        GT = pd.read_csv('calendario_2026.csv', encoding='utf-8', errors='replace')

    # Convert dates
    GT['fecha'] = pd.to_datetime(GT['fecha'])
    
    print(f"Loaded Ground Truth: {len(GT)} rows")
    
    # 2. Extract Layer B Inputs (The Seeds)
    # We assume 'da festivo' (or similar) is the input set by human.
    # We'll normalize column names to handle the '' encoding issue seen in terminal.
    
    clean_cols = {}
    for c in GT.columns:
        if 'da' in c:
            clean = c.replace('da', 'día').replace('despus', 'después').replace('ltimo', 'último').replace('hbil', 'hábil')
            clean_cols[c] = clean
        else:
            clean_cols[c] = c
            
    # For verification, we work with the RAW columns to match the file exactly, 
    # OR we map our logic to the raw column names. 
    # Let's map Logic -> Raw Names found in CSV.
    
    # Identify Event Columns to test offsets for
    # Based on CSV list: 'da de pago de impuestos', 'da de cobro de quincena', 'da festivo'
    # And their offsets: '10 das antes de...'
    
    events_to_test = [
        'da de pago de impuestos',
        'da de cobro de quincena',
        'da festivo',
        'primer da hbil de mes impar', # This is actually Layer C (Derived), but let's test if we can derive its offsets if we treat it as an event? 
        # Wait, 'primer da hbil...' is derived from logic, AND it has offsets derived from it.
        # So it's a chain: Layer B (Festivo) -> Layer C (Primer Habil) -> Layer D (Offsets of Primer Habil).
    ]
    
    # 3. Build our "Computed" DataFrame
    # Start with exact copy of dates and Layer B (Seed events)
    Computed = pd.DataFrame({'fecha': GT['fecha']})
    
    # Copy Layer B seeds from GT (Simulating Human Input)
    # We will assume these are the 'Primary' events
    seed_cols = ['da festivo', 'fin de semana'] # We'll trust GT 'fin de semana' or compute it? Let's compute it to prove we can.
    
    # Let's compute 'fin de semana' from scratch
    Computed['weekday'] = Computed['fecha'].dt.weekday
    Computed['fin de semana'] = Computed['weekday'].isin([5, 6]).astype(int)
    
    # Verify 'fin de semana'
    acc_weekend = (Computed['fin de semana'] == GT['fin de semana']).mean()
    print(f"Accuracy - 'fin de semana': {acc_weekend*100:.2f}%")
    
    # Copy 'da festivo' (Seed)
    if 'da festivo' in GT.columns:
        Computed['da festivo'] = GT['da festivo']
    else:
        # Fallback if encoding differs
        print("Warning: 'da festivo' column not found directly. Checking columns...")
        # (Add fuzzy match logic if needed, but for now specific)
        pass

    # fuzzy finder helper
    def fuzzy_find_col(df, keyword):
        # First pass: try to find exact keyword or keyword with small noise, avoiding 'antes'/'despues'
        candidates = []
        for c in df.columns:
            if 'antes' in c or 'despu' in c or 'después' in c:
                continue
            if keyword in c or keyword.replace('í', '\xad') in c or keyword.replace('í', 'i') in c:
                candidates.append(c)
        
        if candidates:
            # Return shortest match (likely the seed event, not some derivative)
            return min(candidates, key=len)
            
        # Fallback
        for c in df.columns:
             if keyword in c:
                return c
        return None

    # Try to find 'día festivo' column
    festivo_col = fuzzy_find_col(GT, 'festivo')
    if not festivo_col:
        # Try raw pattern seen in terminal
        festivo_col = fuzzy_find_col(GT, 'd\xada festivo')
        
    print(f"Mapped 'festivo' to column: {festivo_col}")

    # --- RECOMPUTE OFFSETS (The Core Test) ---
    print("\n--- Verifying Offset Logic (Layer C) ---")
    
    # For 'da festivo'
    if festivo_col in GT.columns:
        # Copy seed to Computed
        Computed[festivo_col] = GT[festivo_col]
        
        # Run our engine logic
        # We need to normalization of column names in our Engine or pass the RAW name
        # For verification, let's pass the raw name so output matches GT
        Computed = apply_offsets(Computed, festivo_col, N=10)
        
        # Check specific columns
        # We need to construct expected column names based on the raw layout
        # The CSV pattern seems to be: "1 d\xadas antes de..."
        # Let's try to detect the pattern from GT columns
        
        total_checks = 0
        total_correct = 0
        
        for k in range(1, 11):
            # Try to find the matching "before" column in GT
            # Pattern: "{k} ... antes de ... {festivo_col}"?
            # Or just substring search
            before_candidates = [c for c in GT.columns if f'{k} ' in c and 'antes' in c and 'festivo' in c]
            after_candidates = [c for c in GT.columns if f'{k} ' in c and 'despu' in c and 'festivo' in c] # 'despu' handles 'después'/'despus'
            
            if before_candidates:
                gt_col = before_candidates[0]
                # Our engine likely generated it with a cleaner name if we weren't careful.
                # But wait, apply_offsets uses f'{k} das antes de {event_col}'
                # So we need to match our generated name to the GT name.
                
                # Engine generated:
                engine_col = f'{k} das antes de {festivo_col}'
                
                # We need to insure apply_offsets generates the SAME name as GT if we want direct comparison?
                # OR we rename GT column to standard?
                # Easier to check arrays directly.
                
                if engine_col in Computed.columns:
                    # Compare
                    mismatch_mask = Computed[engine_col] != GT[gt_col]
                    matches = (~mismatch_mask).sum()
                    
                    if mismatch_mask.any():
                        print(f"\n[Mismatch] k={k} ({'BEFORE' if 'antes' in gt_col else 'AFTER'})")
                        print(f"Col: {gt_col}")
                        debug_df = pd.DataFrame({
                            'Date': Computed['fecha'],
                            'TargetEvent (Festivo)': Computed[festivo_col],
                            'GT_Offset': GT[gt_col],
                            'My_Offset': Computed[engine_col]
                        })
                        # Show rows where they differ
                        diffs = debug_df[mismatch_mask]
                        print(diffs.head(3))
                        print(f"Example Logic: Date {diffs.iloc[0]['Date']} has GT={diffs.iloc[0]['GT_Offset']} vs My={diffs.iloc[0]['My_Offset']}")
                        
                        # Check if it's a 'Business Day' issue?
                        # Calculate difference in days between this mismatch and the nearest holiday
                        # This debug is getting complex, just showing the row is enough for me to analyze.
                        
                    total_rows = len(GT)
                    total_checks += total_rows
                    total_correct += matches
                else:
                    print(f"Engine failed to generate col: {engine_col}")

            if after_candidates:
                gt_col = after_candidates[0]
                engine_col = f'{k} das despus de {festivo_col}'
                
                if engine_col in Computed.columns:
                    matches = (Computed[engine_col] == GT[gt_col]).sum()
                    total_rows = len(GT)
                    total_checks += total_rows
                    total_correct += matches
        
        if total_checks > 0:
            print(f"Offsets for '{festivo_col}': {total_correct}/{total_checks} ({(total_correct/total_checks)*100:.4f}%)")
        else:
            print("Could not find offset columns in GT to verify.")
        
    else:
        print(f"Skipping festivo test (not found)")

    # --- RECOMPUTE COMPLEX RULES (Labor Rules) ---
    # 'primer da hbil de mes impar'
    # This derives from 'es_habil'.
    
    # 1. Derive es_habil
    # We need 'da festivo' and 'fin de semana'
    # Use the variable festivo_col
    if festivo_col:
        Computed['es_habil'] = ((Computed['fin de semana'] == 0) & (Computed[festivo_col] == 0)).astype(int)
    else:
        print("Warning: Cannot compute es_habil without festivo_col")
        Computed['es_habil'] = 0
    
    # 2. Compute 'primer da hbil de mes impar'
    # Logic: For every month, if odd, find min date where es_habil==1
    Computed['primer da hbil de mes impar'] = 0 # Init
    
    for yr in Computed['fecha'].dt.year.unique():
        for mo in range(1, 13):
            if mo % 2 != 0: # Impar
                # Get days in this month
                mask = (Computed['fecha'].dt.year == yr) & (Computed['fecha'].dt.month == mo)
                days = Computed[mask]
                
                # Find valid business days
                business_days = days[days['es_habil'] == 1]
                
                if not business_days.empty:
                    first_idx = business_days.index[0]
                    Computed.at[first_idx, 'primer da hbil de mes impar'] = 1
                    
    # Compare with GT
    target = 'primer da hbil de mes impar'
    if target in GT.columns:
        acc = (Computed[target] == GT[target]).mean()
        print(f"Accuracy - '{target}': {acc*100:.2f}%")
        if acc < 1.0:
            print("Mismatch found in complex rule. Debugging:")
            mismatches = Computed[Computed[target] != GT[target]]
            print(mismatches[['fecha', 'fin de semana', 'da festivo', target]].head())
    
    # 3. Offsets for the Complex Rule
    # Now verify offsets of 'primer da hbil de mes impar'
    # This proves the chain: Events -> Rules -> Offsets
    Computed = apply_offsets(Computed, target, N=10)
    
    col_check = f'5 das antes de {target}'
    if col_check in GT.columns:
        acc = (Computed[col_check] == GT[col_check]).mean()
        print(f"Accuracy - Chain Offset '{col_check}': {acc*100:.2f}%")

if __name__ == "__main__":
    verify_logic()
