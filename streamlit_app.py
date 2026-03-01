import streamlit as st
import pandas as pd
import src.storage as storage
import src.calendar_engine as engine
from src.ui_components import load_css

st.set_page_config(layout="wide", page_title="Calendar Studio 2026")
load_css()

# --- STATE MANAGEMENT ---
if 'df' not in st.session_state:
    st.session_state.df = storage.load_data()
if 'meta' not in st.session_state:
    st.session_state.meta = storage.load_meta()

# Ensure we have data
if st.session_state.df is None:
    st.warning("No data found. Generating base calendar...")
    year_min = st.session_state.meta.get('year_min', 2022)
    year_max = st.session_state.meta.get('year_max', 2027)
    st.session_state.df = engine.build_base_calendar(year_min, year_max)
    storage.save_data_atomic(st.session_state.df)
    st.rerun()

df = st.session_state.df
meta = st.session_state.meta

# Initialize paint mode state
if 'paint_mode' not in st.session_state:
    st.session_state.paint_mode = "Inspect" 

# --- SIDEBAR: GLOBAL CONTROLS ---
with st.sidebar:
    st.title("Calendar Studio")
    
    st.divider()
    
    st.subheader("⚙️ Configuración")
    col_min, col_max = st.columns(2)
    with col_min:
        new_year_min = st.number_input("Año Inicio", min_value=2020, max_value=2050, value=st.session_state.meta.get('year_min', 2022))
    with col_max:
        new_year_max = st.number_input("Año Fin", min_value=2020, max_value=2050, value=st.session_state.meta.get('year_max', 2027))
        
    if st.button("🔄 Generar Nuevo Base"):
        st.session_state.meta['year_min'] = new_year_min
        st.session_state.meta['year_max'] = new_year_max
        storage.save_meta(st.session_state.meta)
        with st.spinner("Construyendo años..."):
            st.session_state.df = engine.build_base_calendar(new_year_min, new_year_max)
            storage.save_data_atomic(st.session_state.df)
        st.success("Rango de años actualizado.")
        st.rerun()
        
    st.divider()
    
    # Recalculate Button
    if st.button("🚀 Recalcular Reglas (Engine)", type="primary"):
        with st.spinner("Aplicando lógica matemática y Offsets..."):
            active_events = [e for e in meta['events'] if e.get('enabled', True)]
            new_df = engine.run_recalculation_pipeline(df.copy(), active_events)
            st.session_state.df = new_df
            storage.save_data_atomic(new_df)
        st.success("Calendario Actualizado!")
        st.rerun()

    if st.session_state.df is not None:
        csv_data = st.session_state.df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Descargar Calendario (CSV)",
            data=csv_data,
            file_name=f"calendario_studio_export.csv",
            mime="text/csv"
        )

    st.divider()
    
    # Paint Mode Selector
    st.subheader("🖊️ Paint Mode")
    paint_options = ["Inspect"] + [e['name'] for e in meta['events']]
    st.session_state.paint_mode = st.radio("Tool", paint_options, label_visibility="collapsed")
    
    st.caption("Select a tool above, then click on the calendar to apply.")

    st.divider()
    
    # Event Manager (Global Config)
    st.subheader("Event Types & Offsets")
    
    # FOCUS LOGIC: Determine which event is editable
    active_paint_tool = st.session_state.get('paint_mode', 'Inspect')
    
    for i, evt in enumerate(meta['events']):
        evt_name = evt['name']
        
        # Determine State
        is_focused = (active_paint_tool == evt_name)
        is_inspect = (active_paint_tool == "Inspect")
        
        # State Logic:
        # If Inspect -> Locked (Collapsed)
        # If Paint Tool -> Only that tool Editable (Expanded)
        # Others -> Locked (Collapsed)
        
        should_expand = is_focused
        is_disabled = not is_focused
        
        # Label with visual cue
        c_label = f"{evt_name} {evt.get('symbol', '🔹')}"
        if is_focused: c_label = "🟢 " + c_label
        elif is_disabled: c_label = "🔒 " + c_label
        
        with st.expander(c_label, expanded=should_expand):
            if is_disabled:
                st.caption(f"Select '{evt_name}' in Paint Mode above to edit.")
            else:
                # EDITABLE CONTROLS
                c1, c2 = st.columns(2)
                with c1:
                    new_color = st.color_picker("Color", evt['color'], key=f"c_{evt_name}")
                    # PERSISTENCE FIX: Update meta if color changes
                    if new_color != evt['color']:
                        meta['events'][i]['color'] = new_color
                        st.session_state.meta = meta
                        storage.save_meta(meta)
                        st.rerun()
                        
                with c2:
                    current_sym = evt.get('symbol', '🔹')
                    new_sym = st.text_input("Symbol", value=current_sym, key=f"sym_{evt_name}")
                    if new_sym != current_sym:
                        meta['events'][i]['symbol'] = new_sym
                        st.session_state.meta = meta
                        storage.save_meta(meta)
                        st.rerun()

                # Live Color Preview (To prove we know the color)
                st.markdown(f"**Preview:** <span style='color:{new_color}; font-size:1.5em;'>{evt.get('symbol', '')}</span>", unsafe_allow_html=True)

                current_n = evt.get('offset_days', 10)
                new_n = st.number_input(f"Offset ±Days", min_value=0, max_value=30, value=current_n, key=f"global_offset_{evt_name}")
                
                if new_n != current_n:
                    meta['events'][i]['offset_days'] = new_n
                    st.session_state.meta = meta
                    storage.save_meta(meta)

# --- MAIN LAYOUT ---

tab_calendar, tab_data = st.tabs(["🗓️ Calendar Studio", "🗃️ Data Management"])

with tab_calendar:
    years = sorted(df['año'].unique())
    tabs = st.tabs([str(y) for y in years])

    for i, year in enumerate(years):
        with tabs[i]:
            col_cal, col_inspector = st.columns([3, 2])
            
            with col_cal:
                st.subheader(f"Calendar {year}")
                
                df_year = df[df['año'] == year]
                
                for month in range(1, 13):
                    df_month = df_year[df_year['mes'] == month]
                    if df_month.empty:
                        continue
                        
                    msg_month = pd.to_datetime(f"{year}-{month}-01").strftime("%B")
                    
                    with st.expander(msg_month, expanded=(month==1)):
                        cols = st.columns(7)
                        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                        for idx, d in enumerate(days):
                            cols[idx].write(f"**{d}**")
                            
                        first_day_weekday = df_month.iloc[0]['weekday']
                        current_col = 0
                        row_cols = st.columns(7)
                        
                        for _ in range(first_day_weekday):
                            row_cols[current_col].write("")
                            current_col += 1
                            
                        for _, row in df_month.iterrows():
                            if current_col > 6:
                                current_col = 0
                                row_cols = st.columns(7)
                            
                            day_num = row['dia']
                            date_str = row['fecha'].strftime("%Y-%m-%d")
                            
                            # VISUALIZATION LABEL
                            label = f"{day_num}"
                            
                            # Helper for Streamlit Colors
                            def get_streamlit_color(hex_code):
                                # Simple mapping to standard streamlit markdown colors (:red, :green, etc)
                                # We measure distance to known palette
                                import math
                                
                                if not hex_code.startswith('#'): return ''
                                
                                # Standard Streamlit Colors (Approximate Hex)
                                palette = {
                                    'red': (255, 75, 75),
                                    'orange': (255, 164, 33),
                                    'green': (33, 195, 84),
                                    'blue': (28, 131, 225),
                                    'violet': (128, 61, 245),
                                    'gray': (128, 128, 128),
                                }
                                
                                # Parse Input
                                h = hex_code.lstrip('#')
                                try:
                                    r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                                except:
                                    return ''
                                    
                                # Find closest
                                min_dist = float('inf')
                                chosen_name = ''
                                
                                for name, (pr, pg, pb) in palette.items():
                                    dist = math.sqrt((r-pr)**2 + (g-pg)**2 + (b-pb)**2)
                                    if dist < min_dist:
                                        min_dist = dist
                                        chosen_name = name
                                
                                return chosen_name

                            # Check Events (Accumulate Symbols)
                            active_symbols_str = ""
                            for evt in meta['events']:
                                if row.get(evt['name'], 0) == 1:
                                    sym = evt.get('symbol', '🔹')
                                    hex_c = evt.get('color', '#888888')
                                    st_col = get_streamlit_color(hex_c)
                                    
                                    # Append styled symbol
                                    if st_col:
                                        active_symbols_str += f" :{st_col}[{sym}]"
                                    else:
                                        active_symbols_str += f" {sym}"
                                    
                            if active_symbols_str:
                                label += active_symbols_str
                                
                            # Determinar estilo del botón según si es hábil o no
                            btn_type = "primary" if row.get("es_habil", 0) == 1 else "secondary"
                                
                            # BUTTON INTERACTION
                            if row_cols[current_col].button(label, key=f"btn_{date_str}", type=btn_type):
                                active_tool = st.session_state.paint_mode
                                
                                if active_tool == "Inspect":
                                    st.session_state.selected_date = date_str
                                    st.rerun()
                                else:
                                    idx = row.name 
                                    current_val = df.at[idx, active_tool]
                                    new_val = 0 if current_val == 1 else 1
                                    df.at[idx, active_tool] = new_val
                                    storage.save_data_atomic(df)
                                    
                                    # Bidirectional CSV Sync
                                    import os
                                    # Identificamos si el 'active_tool' tiene un CSV homólogo
                                    # Basado en nuestras reglas: día festivo -> festivos.csv, etc.
                                    map_csv = {
                                        'día festivo': 'festivos.csv',
                                        'día de pago de impuestos': 'impuestos.csv',
                                        'día de cobro de quincena': 'quincenas.csv'
                                    }
                                    
                                    if active_tool in map_csv:
                                        target_csv = map_csv[active_tool]
                                        if os.path.exists(target_csv):
                                            df_target = pd.read_csv(target_csv)
                                            
                                            if new_val == 1:
                                                # Añadir fecha
                                                if date_str not in df_target['fecha'].values:
                                                    df_target = pd.concat([df_target, pd.DataFrame({'fecha': [date_str]})], ignore_index=True)
                                                    df_target = df_target.sort_values('fecha')
                                            else:
                                                # Quitar fecha
                                                df_target = df_target[df_target['fecha'] != date_str]
                                                
                                            df_target.to_csv(target_csv, index=False)
                                            
                                    st.rerun()
                            current_col += 1

            with col_inspector:
                st.subheader("Day Inspector")
                
                if 'selected_date' in st.session_state:
                    sel_date = st.session_state.selected_date
                    
                    if str(year) in sel_date:
                        st.write(f"**Selected:** {sel_date}")
                        
                        mask = df['fecha'] == sel_date
                        if mask.any():
                            row = df[mask].iloc[0]
                            
                            # Define Column Groups
                            base_primary_cols = ['año', 'mes', 'dia', 'weekday', 'es_habil', 'fin de semana']
                            events_cols = [e['name'] for e in meta['events']] + [
                                'primer día hábil de mes impar', 'último día hábil de mes impar', 
                                'primer día hábil de mes par', 'último día hábil de mes par'
                            ]
                            offset_cols = [c for c in df.columns if 'antes' in c or 'después' in c]
                            
                            base_secondary_cols = [c for c in df.columns if c not in base_primary_cols + events_cols + offset_cols + ['fecha']]

                            # Block 1: base-primary
                            with st.expander("base-primary", expanded=True):
                                grid_p = {"Metric": [], "Value": []}
                                for c in base_primary_cols:
                                    if c in row:
                                        grid_p["Metric"].append(c)
                                        val = row[c]
                                        # Formato booleano para los flags (0/1)
                                        if c in ['es_habil', 'fin de semana']:
                                            val = bool(val)
                                        grid_p["Value"].append(str(val))
                                st.table(pd.DataFrame(grid_p))

                            # Block 2: base-secondary
                            with st.expander("base-secondary", expanded=True):
                                active_sec = [c for c in base_secondary_cols if c in row and row[c] == 1]
                                if active_sec:
                                    st.write("**Active:**")
                                    for sec in active_sec:
                                        st.markdown(f"- {sec}")
                                else:
                                    st.caption("No active secondary elements")

                            # Block 3: events
                            with st.expander("events", expanded=True):
                                found_any = False
                                for c in events_cols:
                                    if c in row and row[c] == 1:
                                        found_any = True
                                        # Si es de meta, pintar su color y símbolo.
                                        meta_evt = next((e for e in meta['events'] if e['name'] == c), None)
                                        if meta_evt:
                                            color = meta_evt['color']
                                            sym = meta_evt.get('symbol', '')
                                            st.markdown(f"<div style='color: {color}; font-weight: bold; margin-bottom: 4px;'>{sym} {c}</div>", unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"<div style='font-weight: bold; margin-bottom: 4px;'>⚙️ {c}</div>", unsafe_allow_html=True)
                                            
                                if not found_any:
                                    st.caption("No events active")

                            # Block 4: events-offset
                            with st.expander("events-offset", expanded=True):
                                active_off = [c for c in offset_cols if c in row and row[c] == 1]
                                if active_off:
                                    st.write("**Active Offsets:**")
                                    for o in active_off:
                                        st.markdown(f"- {o}")
                                else:
                                    st.caption("No active offsets")
                    else:
                        st.empty()

with tab_data:
    st.header("🗃️ Manage Base Files (.csv)")
    st.write("Edita directamente las reglas de calidad o las fechas de los eventos base (festivos, impuestos...). **Asegúrate de no corromper la estructura (nombres de columna o formato YYYY-MM-DD).**")
    
    import glob
    import os
    
    csv_files = glob.glob("*.csv")
    csv_files = [f for f in csv_files if f != "calendario_2026.csv"] # Omit old backsups just in case
    
    if csv_files:
        selected_csv = st.selectbox("Selecciona un archivo a editar:", sorted(csv_files))
        
        if selected_csv:
            try:
                # Read specific file
                df_editor = pd.read_csv(selected_csv)
                
                # Show editor
                st.subheader(f"Editando: {selected_csv}")
                edited_df = st.data_editor(
                    df_editor, 
                    num_rows="dynamic",
                    width="stretch",
                    key=f"editor_{selected_csv}"
                )
                
                # Save manual changes back to CSV
                if st.button(f"💾 Guardar cambios en {selected_csv}", type="primary"):
                    try:
                        edited_df.to_csv(selected_csv, index=False)
                        st.success(f"Archivo {selected_csv} guardado exitosamente. No olvides dar click en 'Recalculate Rules (Engine)' para que impacte el calendario global.")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
            except Exception as e:
                st.error(f"Error parseando archivo: {e}")
    else:
        st.info("No se encontraron archivos CSV en el directorio base.")
