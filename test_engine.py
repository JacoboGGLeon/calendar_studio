import pandas as pd
import sys
sys.path.append('.')
from src.calendar_engine import build_base_calendar, run_recalculation_pipeline

def main():
    print("Testing Calendar Engine vs CSV...")
    
    # Load original CSV
    csv_file = 'calendario_2026.csv'
    try:
        df_csv = pd.read_csv(csv_file, parse_dates=['fecha'])
        # Filter to only 2026 if necessary, although CSV might have more.
        # Wait, the CSV I saw had 2022. The filename is "calendario_2026.csv", 
        # but rows are from 2022. I'll read everything.
        df_csv['fecha'] = pd.to_datetime(df_csv['fecha'])
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")
        return
        
    year_min = df_csv['fecha'].dt.year.min()
    year_max = df_csv['fecha'].dt.year.max()
    
    # Generate generated DataFrame
    df_gen_base = build_base_calendar(year_min, year_max)
    
    # Filter to exact dates in CSV
    df_gen_base = df_gen_base[df_gen_base['fecha'].isin(df_csv['fecha'])].copy().reset_index(drop=True)
    df_csv = df_csv.reset_index(drop=True)
    
    # We must construct a 'día festivo' column to match the CSV's events
    if 'día festivo' in df_csv.columns:
        df_gen_base['día festivo'] = df_csv['día festivo']
        
    df_gen = run_recalculation_pipeline(df_gen_base, [])
    
    # Compare
    missing_in_gen = set(df_csv.columns) - set(df_gen.columns)
    missing_in_csv = set(df_gen.columns) - set(df_csv.columns)
    
    print(f"Columns missing in generated: {missing_in_gen}")
    print(f"Columns missing in CSV: {missing_in_csv}")
    
    # Diff shapes
    print(f"CSV Shape: {df_csv.shape} | Gen Shape: {df_gen.shape}")
    
    # Align and test logic strictly
    cols_to_check = [c for c in df_csv.columns if c in df_gen.columns and c != 'fecha']
    
    with open('test_diff.log', 'w', encoding='utf-8') as f:
        errors = 0
        for col in cols_to_check:
            csv_col = df_csv[col].fillna(0).astype(int)
            gen_col = df_gen[col].fillna(0).astype(int)
            
            diff = (csv_col != gen_col).sum()
            if diff > 0:
                f.write(f"MISMATCH in column '{col}': {diff} rows differ.\n")
                errors += 1
                if col in ['día par del mes', 'inicio del bimestre contable 1', 'día de cobro de quincena']:
                    diff_idx = df_csv.index[csv_col != gen_col]
                    f.write(f"  Sample diffs for {col}:\n")
                    for i in diff_idx[:5]:
                        f.write(f"    Date {df_csv.at[i, 'fecha'].date()}: CSV={csv_col.at[i]}, Gen={gen_col.at[i]}\n")
                
        if errors == 0 and len(missing_in_gen) == 0:
            f.write("SUCCESS! 100% Match.\n")
            print("SUCCESS!")
        else:
            msg = f"FAILED with {errors} logic mismatches."
            f.write(msg + "\n")
            print(msg)

if __name__ == '__main__':
    main()
