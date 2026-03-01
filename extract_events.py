import pandas as pd
import os

def extract_events():
    original_csv = 'calendario_2026.csv'
    if not os.path.exists(original_csv):
        print(f"Error: {original_csv} no encontrado.")
        return
        
    df = pd.read_csv(original_csv)
    
    # Eventos a extraer
    eventos = {
        'festivos': 'día festivo',
        'quincenas': 'día de cobro de quincena',
        'impuestos': 'día de pago de impuestos'
    }
    
    for filename, col_name in eventos.items():
        if col_name in df.columns:
            # Filtrar solo las fechas donde el evento es 1
            df_evento = df[df[col_name] == 1][['fecha']].copy()
            df_evento.to_csv(f'{filename}.csv', index=False)
            print(f"Extráidos {len(df_evento)} registros para '{col_name}' en {filename}.csv")
        else:
            print(f"Columna {col_name} no encontrada en el CSV original.")

if __name__ == '__main__':
    extract_events()
