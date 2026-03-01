import pandas as pd
import datetime

# --- FUNCIONES AUXILIARES DE SALTO (LEAP) ---

def backward_leap_to_habil(df, target_days):
    """
    Dada una lista de df.index o target_days (boolean mask),
    busca hacia atrás el día hábil más cercano para cada ocurrencia.
    """
    res = pd.Series(0, index=df.index)
    if isinstance(target_days, pd.Series):
        target_idxs = df.index[target_days].tolist()
    else:
        target_idxs = target_days
        
    for idx in target_idxs:
        curr_idx = idx
        while curr_idx >= 0 and df.at[curr_idx, 'es_habil'] == 0:
            curr_idx -= 1
        if curr_idx >= 0:
            res.at[curr_idx] = 1
    return res

def forward_leap_to_habil(df, target_days):
    """
    Busca hacia adelante el día hábil más cercano.
    """
    res = pd.Series(0, index=df.index)
    if isinstance(target_days, pd.Series):
        target_idxs = df.index[target_days].tolist()
    else:
        target_idxs = target_days
        
    max_idx = len(df) - 1
    for idx in target_idxs:
        curr_idx = idx
        while curr_idx <= max_idx and df.at[curr_idx, 'es_habil'] == 0:
            curr_idx += 1
        if curr_idx <= max_idx:
            res.at[curr_idx] = 1
    return res

# --- FUNCIONES DE OFFSET ---

def compute_working_offset_backward(df, col, K):
    res = pd.Series(0, index=df.index)
    event_idxs = df.index[df[col] == 1].tolist()
    
    for idx in event_idxs:
        steps = 0
        curr_idx = idx
        while steps < K and curr_idx > 0:
            curr_idx -= 1
            if df.at[curr_idx, 'es_habil'] == 1:
                steps += 1
        
        if steps == K:
            # Regla de supresión: si el destino TAMBIÉN es el evento, no marcarlo
            if df.at[curr_idx, col] != 1:
                res.at[curr_idx] = 1
    return res

def compute_working_offset_forward(df, col, K):
    res = pd.Series(0, index=df.index)
    event_idxs = df.index[df[col] == 1].tolist()
    max_idx = len(df) - 1
    
    for idx in event_idxs:
        steps = 0
        curr_idx = idx
        while steps < K and curr_idx < max_idx:
            curr_idx += 1
            if df.at[curr_idx, 'es_habil'] == 1:
                steps += 1
                
        if steps == K:
            if df.at[curr_idx, col] != 1:
                res.at[curr_idx] = 1
    return res

# --- ENGINE INTERFACE ---

def build_base_calendar(year_min, year_max):
    """
    Construye las variables primarias y secundarias (No Negociables).
    """
    dates = pd.date_range(start=f'{year_min}-01-01', end=f'{year_max}-12-31', freq='D')
    df = pd.DataFrame({'fecha': dates})
    
    # Dummies de Días 1 al 31
    for i in range(1, 32):
        df[f'día {i}'] = (df['fecha'].dt.day == i).astype(int)
        
    # Dummies de Día de la Semana
    dias_semana = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes']
    for i, dia_str in enumerate(dias_semana):
        df[f'día {dia_str}'] = (df['fecha'].dt.weekday == i).astype(int)
        
    # Fin de semana
    df['fin de semana'] = df['fecha'].dt.weekday.isin([5, 6]).astype(int)
    
    # Dummies de Mes
    meses_nombres = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                     'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    for i, mes_str in enumerate(meses_nombres):
        df[f'mes de {mes_str}'] = (df['fecha'].dt.month == (i + 1)).astype(int)
        
    # Atributos Auxiliares y compatibilidad
    # ATENCION: El CSV original define "día par/impar del mes" basándose en el MES, no en el día.
    df['día par del mes'] = (df['fecha'].dt.month % 2 == 0).astype(int)
    df['día impar del mes'] = (df['fecha'].dt.month % 2 != 0).astype(int)
    
    df['año'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    df['dia'] = df['fecha'].dt.day
    df['weekday'] = df['fecha'].dt.weekday

    # Periodos
    df['bimestre_num'] = df['fecha'].dt.month.apply(lambda x: (x-1)//2 + 1)
    for i in range(1, 7):
        df[f'bimestre {i} del año'] = (df['bimestre_num'] == i).astype(int)
        
    df['trimestre_num'] = df['fecha'].dt.month.apply(lambda x: (x-1)//3 + 1)
    for i in range(1, 5):
        df[f'trimestre {i} del año'] = (df['trimestre_num'] == i).astype(int)
        
    df['cuatrimestre_num'] = df['fecha'].dt.month.apply(lambda x: (x-1)//4 + 1)
    for i in range(1, 4):
        df[f'cuatrimestre {i} del año'] = (df['cuatrimestre_num'] == i).astype(int)
        
    df['semestre_num'] = df['fecha'].dt.month.apply(lambda x: (x-1)//6 + 1)
    for i in range(1, 3):
        df[f'semestre {i} del año'] = (df['semestre_num'] == i).astype(int)

    # Inicios y Cierres de Periodos (Mensuales, fijos según el calendario gregoriano)
    period_months = {
        'bimestre': {1: (1, 2), 2: (3, 4), 3: (5, 6), 4: (7, 8), 5: (9, 10), 6: (11, 12)},
        'trimestre': {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)},
        'cuatrimestre': {1: (1, 4), 2: (5, 8), 3: (9, 12)},
        'semestre': {1: (1, 6), 2: (7, 12)}
    }
    
    for period_str, num_col in [('bimestre', 'bimestre_num'), ('trimestre', 'trimestre_num'), 
                                ('cuatrimestre', 'cuatrimestre_num'), ('semestre', 'semestre_num')]:
        for i in df[num_col].dropna().unique():
            if period_str == 'bimestre' and i <= 3:
                inicio_col = f'inicio del {period_str} contable {i}'
            else:
                inicio_col = f'inicio del {period_str} {i}'
                
            cierre_col = f'cierre del {period_str} {i}'
            
            i_month, c_month = period_months[period_str][int(i)]
            
            df[inicio_col] = ((df['fecha'].dt.month == i_month) & (df[num_col] == i)).astype(int)
            df[cierre_col] = ((df['fecha'].dt.month == c_month) & (df[num_col] == i)).astype(int)

    # Anual
    df['inicio del anual'] = (df['fecha'].dt.month == 1).astype(int)
    df['cierre del anual'] = (df['fecha'].dt.month == 12).astype(int)

    # Cleanup iterators
    df = df.drop(columns=['bimestre_num', 'trimestre_num', 'cuatrimestre_num', 'semestre_num'])
    
    return df

def run_recalculation_pipeline(df, event_configs):
    """
    Ejecuta toda la lógica de Reglas de Dominio y Calidad.
    1. es_habil
    2. pagos y quincenas con leaps
    3. primer/último día hábil
    4. offsets
    """
    # 1. ES_HABIL
    if 'día festivo' not in df.columns:
        df['día festivo'] = 0
        
    df['es_habil'] = ((df['fin de semana'] == 0) & (df['día festivo'] == 0)).astype(int)

    # 2. PAGOS Y COBROS (LEAPS)
    # Impuestos: Día 17 o hábil posterior
    mask_17 = df['dia'] == 17
    df['día de pago de impuestos'] = forward_leap_to_habil(df, mask_17)
    
    # Quincena: Día 15 y fin de mes, o hábil anterior
    fin_de_mes = df.groupby(['año', 'mes'])['fecha'].transform('max')
    mask_quincena = (df['dia'] == 15) | (df['fecha'] == fin_de_mes)
    df['día de cobro de quincena'] = backward_leap_to_habil(df, mask_quincena)

    # 3. PRIMER / ÚLTIMO DÍA HÁBIL DE MES IMPAR/PAR
    df['primer día hábil de mes impar'] = 0
    df['último día hábil de mes impar'] = 0
    df['primer día hábil de mes par'] = 0
    df['último día hábil de mes par'] = 0
    
    habil_df = df[df['es_habil'] == 1]
    if not habil_df.empty:
        primeros = habil_df.groupby(['año', 'mes'])['fecha'].idxmin()
        ultimos = habil_df.groupby(['año', 'mes'])['fecha'].idxmax()
        
        primeros_impar = primeros[primeros.index.get_level_values('mes') % 2 != 0].values
        primeros_par = primeros[primeros.index.get_level_values('mes') % 2 == 0].values
        
        ultimos_impar = ultimos[ultimos.index.get_level_values('mes') % 2 != 0].values
        ultimos_par = ultimos[ultimos.index.get_level_values('mes') % 2 == 0].values
        
        df.loc[primeros_impar, 'primer día hábil de mes impar'] = 1
        df.loc[ultimos_impar, 'último día hábil de mes impar'] = 1
        df.loc[primeros_par, 'primer día hábil de mes par'] = 1
        df.loc[ultimos_par, 'último día hábil de mes par'] = 1

    # 4. OFFSETS (En días hábiles)
    # Identificar qué eventos requieren offset según el CSV
    eventos_con_offset = [
        'día de pago de impuestos',
        'día de cobro de quincena',
        'día festivo',
        'primer día hábil de mes impar',
        'último día hábil de mes impar',
        'primer día hábil de mes par',
        'último día hábil de mes par'
    ]
    
    N = 10
    
    # Initialize all columns to 0 first to respect EXACT csv structure
    for event_col in eventos_con_offset:
        for k in reversed(range(1, N+1)):
            df[f'{k} días antes de {event_col}'] = 0
        for k in range(1, N+1):
            df[f'{k} días después de {event_col}'] = 0
    
    # Calculate values
    for event_col in eventos_con_offset:
        if event_col in df.columns:
            for k in range(1, N+1):
                pre_col = f'{k} días antes de {event_col}'
                post_col = f'{k} días después de {event_col}'
                
                df[pre_col] = compute_working_offset_backward(df, event_col, k)
                df[post_col] = compute_working_offset_forward(df, event_col, k)
                
    return df
