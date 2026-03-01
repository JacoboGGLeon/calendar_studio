import pandas as pd

def generate_rules_csv():
    rules = []
    
    # helper for appending
    def add_rule(id_col, col_name, rule_desc, code_str):
        rules.append({
            'id_column': id_col,
            'column': col_name,
            'rule': rule_desc,
            'code': code_str
        })
        
    # 1. Base Dates
    add_rule('fecha', 'fecha', 'Clave Primaria: la fecha base', "fechas_rango") # This might be handled outside, but for completion
    add_rule('ano', 'año', 'El año geométrico', "df['fecha'].dt.year")
    add_rule('mes', 'mes', 'El número de mes', "df['fecha'].dt.month")
    add_rule('dia', 'dia', 'El número de día', "df['fecha'].dt.day")
    add_rule('weekday', 'weekday', 'Día de la semana numérico', "df['fecha'].dt.weekday")
    
    # 2. Dias del mes
    for i in range(1, 32):
        add_rule(f'dia_{i}', f'día {i}', f'Bandera para el día {i} del mes', f"(df['fecha'].dt.day == {i}).astype(int)")

    # 3. Dias de la semana
    dias_semana = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes']
    for i, d in enumerate(dias_semana):
        add_rule(f'dia_{d}', f'día {d}', f'Bandera para el día {d}', f"(df['fecha'].dt.weekday == {i}).astype(int)")
        
    add_rule('fin_de_semana', 'fin de semana', 'Sábado o Domingo', "df['fecha'].dt.weekday.isin([5, 6]).astype(int)")
    add_rule('dia_par_del_mes', 'día par del mes', 'Basado en el mes par', "(df['fecha'].dt.month % 2 == 0).astype(int)")
    add_rule('dia_impar_del_mes', 'día impar del mes', 'Basado en el mes impar', "(df['fecha'].dt.month % 2 != 0).astype(int)")
    
    # 4. Meses
    meses_nombres = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                     'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    for i, m in enumerate(meses_nombres):
        add_rule(f'mes_{m}', f'mes de {m}', f'Bandera para el mes de {m}', f"(df['fecha'].dt.month == {i+1}).astype(int)")
        
    # 5. Periodos (Flags) - In the real engine, we built them inside. For CSV, we can abstract them.
    for i in range(1, 7):
        add_rule(f'bimestre_{i}_del_ano', f'bimestre {i} del año', f'Bimestre {i}', f"(df['fecha'].dt.month.apply(lambda x: (x-1)//2 + 1) == {i}).astype(int)")
    for i in range(1, 5):
        add_rule(f'trimestre_{i}_del_ano', f'trimestre {i} del año', f'Trimestre {i}', f"(df['fecha'].dt.month.apply(lambda x: (x-1)//3 + 1) == {i}).astype(int)")
    for i in range(1, 4):
        add_rule(f'cuatrimestre_{i}_del_ano', f'cuatrimestre {i} del año', f'Cuatrimestre {i}', f"(df['fecha'].dt.month.apply(lambda x: (x-1)//4 + 1) == {i}).astype(int)")
    for i in range(1, 3):
        add_rule(f'semestre_{i}_del_ano', f'semestre {i} del año', f'Semestre {i}', f"(df['fecha'].dt.month.apply(lambda x: (x-1)//6 + 1) == {i}).astype(int)")

    # 6. Inicios y Cierres
    period_months = {
        'bimestre': {1: (1, 2), 2: (3, 4), 3: (5, 6), 4: (7, 8), 5: (9, 10), 6: (11, 12)},
        'trimestre': {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)},
        'cuatrimestre': {1: (1, 4), 2: (5, 8), 3: (9, 12)},
        'semestre': {1: (1, 6), 2: (7, 12)}
    }
    for p_type, cfg in period_months.items():
        for i, (m_start, m_end) in cfg.items():
            if p_type == 'bimestre' and i <= 3:
                c_name_start = f'inicio del {p_type} contable {i}'
            else:
                c_name_start = f'inicio del {p_type} {i}'
            c_name_end = f'cierre del {p_type} {i}'
            
            add_rule(f'inicio_{p_type}_{i}', c_name_start, f'Mes inicio de {p_type} {i}', f"((df['fecha'].dt.month == {m_start}) & (df['fecha'].dt.month.apply(lambda x: (x-1)//{12//len(cfg)} + 1) == {i})).astype(int)")
            add_rule(f'cierre_{p_type}_{i}', c_name_end, f'Mes cierre de {p_type} {i}', f"((df['fecha'].dt.month == {m_end}) & (df['fecha'].dt.month.apply(lambda x: (x-1)//{12//len(cfg)} + 1) == {i})).astype(int)")

    add_rule('inicio_anual', 'inicio del anual', 'Mes de enero general', "(df['fecha'].dt.month == 1).astype(int)")
    add_rule('cierre_anual', 'cierre del anual', 'Mes de diciembre general', "(df['fecha'].dt.month == 12).astype(int)")

    # 7. Layer B - Logic Rules
    # Ahora leen dinámicamente desde sus archivos semillas extraídos
    add_rule('dia_festivo', 'día festivo', 'Semilla estática cargada desde festivos.csv', "df['fecha'].dt.strftime('%Y-%m-%d').isin(pd.read_csv('festivos.csv')['fecha']).astype(int)")
    add_rule('es_habil', 'es_habil', 'Día laborable sin festivos', "((df['fin de semana'] == 0) & (df['día festivo'] == 0)).astype(int)")
    
    # 8. Events
    add_rule('dia_pago_impuestos', 'día de pago de impuestos', 'Semilla estática cargada desde impuestos.csv', "df['fecha'].dt.strftime('%Y-%m-%d').isin(pd.read_csv('impuestos.csv')['fecha']).astype(int)")
    add_rule('dia_cobro_quincena', 'día de cobro de quincena', 'Semilla estática cargada desde quincenas.csv', "df['fecha'].dt.strftime('%Y-%m-%d').isin(pd.read_csv('quincenas.csv')['fecha']).astype(int)")

    add_rule('primer_dia_habil_impar', 'primer día hábil de mes impar', 'Algoritmo min date impar', "compute_first_last_working(df, 'primer', 'impar')")
    add_rule('ultimo_dia_habil_impar', 'último día hábil de mes impar', 'Algoritmo max date impar', "compute_first_last_working(df, 'ultimo', 'impar')")
    add_rule('primer_dia_habil_par', 'primer día hábil de mes par', 'Algoritmo min date par', "compute_first_last_working(df, 'primer', 'par')")
    add_rule('ultimo_dia_habil_par', 'último día hábil de mes par', 'Algoritmo max date par', "compute_first_last_working(df, 'ultimo', 'par')")

    # 9. Offsets
    eventos_offset = [
        'día de pago de impuestos', 'día de cobro de quincena', 'día festivo',
        'primer día hábil de mes impar', 'último día hábil de mes impar',
        'primer día hábil de mes par', 'último día hábil de mes par'
    ]
    
    for evt in eventos_offset:
        evt_id = evt.replace(' ', '_').replace('í', 'i')
        for k in range(1, 11):
            add_rule(f'{k}_dias_antes_{evt_id}', f'{k} días antes de {evt}', f'{k} dias atras en dias habiles', f"compute_working_offset_backward(df, '{evt}', {k})")
            add_rule(f'{k}_dias_despues_{evt_id}', f'{k} días después de {evt}', f'{k} dias adelante en dias habiles', f"compute_working_offset_forward(df, '{evt}', {k})")
            
    # Save
    df_rules = pd.DataFrame(rules)
    df_rules.to_csv('reglas_calidad.csv', index=False)
    print("reglas_calidad.csv generado exitosamente con", len(df_rules), "reglas.")

if __name__ == '__main__':
    generate_rules_csv()
