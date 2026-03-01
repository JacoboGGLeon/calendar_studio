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
