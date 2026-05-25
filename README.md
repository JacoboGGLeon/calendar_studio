# Calendar Studio 2026

Una aplicación construida en Python (Streamlit + Pandas) diseñada para generar calendarios matemáticos precisos con complejas reglas de negocio (Periodos, Días Hábiles, Saltos de Pago y Cobro de Quincenas dinámicos).

El motor "Calendar Engine" sustituye la necesidad de gestionar offsets manuales en Excel, asegurando un **100% de precisión lógica**.

## Funcionalidades
1. **Generación Continua:** Define años de inicio y fin para crear al instante la base del calendario (1/0) de todos los períodos contables.
2. **Re-calculadora Dinámica:** Configura los Días Festivos con la brocha de la interfaz y el motor ajustará inmediatamente los saltos (*forward/backward leaps*) y los márgenes de seguridad (`K días después de...`).
3. **Exportador Universal:** Descarga la macro-tabla en `.csv` para alimentar otros modelos de datos o reportes.

## Cómo Ejecutar (Localmente)

1. Clona el repositorio:
```bash
git clone <tu-repo-url>
cd calendar
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Inicia la aplicación:
```bash
streamlit run streamlit_app.py
```

## Estructura del Código
- `streamlit_app.py`: La interfaz principal gráfica de inspección y "pintado" de eventos.
- `src/calendar_engine.py`: El corazón matemático. Aquí habitan las reglas de "calidad" y las funciones `forward_leap` y `backward_leap`.
- `src/storage.py`: Manejo de estado persistente entre reinicios de la aplicación utilizando el file system local.


## Reglas de negocio consolidadas

El motor trata este archivo como un **calendario de días hábiles**:

1. La única fuente manual fuerte es `festivos.csv`.
2. `fin de semana` se calcula desde la fecha: sábado y domingo.
3. `es_habil` se calcula internamente como `fin de semana == 0` y `día festivo == 0`.
4. `día de cobro de quincena` se deriva desde los días teóricos 15 y 30:
   - si el día teórico no es hábil, se mueve hacia atrás hasta el día hábil inmediato;
   - en meses sin día 30, como febrero, se usa el último día real del mes y se mueve hacia atrás si hace falta.
5. `día de pago de impuestos` se deriva desde el día 17:
   - si el 17 no es hábil, se mueve hacia adelante hasta el día hábil inmediato.
6. Los offsets `N días antes/después de ...` se cuentan exclusivamente en días hábiles.

## Contrato de salida

El export final debe respetar exactamente el layout requerido por los sistemas downstream:

- 246 columnas.
- Primera columna: `fecha`.
- Todas las demás columnas enteras `0/1`.
- Sin columnas auxiliares internas como `año`, `mes`, `dia`, `weekday` o `es_habil`.
- La función `calendar_engine.to_required_output_layout(df)` normaliza el DataFrame antes de exportarlo.
- La descarga de Streamlit ya usa este layout contractual.
