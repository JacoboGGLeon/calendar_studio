# Calendar Studio

Librería independiente para generar calendarios con reglas explícitas, validarlos y conservarlos como artefactos reproducibles. Python 3.11+, Pandas, Pydantic y Parquet. No necesita Model Arena, AWS ni Streamlit para generar calendarios.

```bash
python -m pip install "calendar-studio==0.1.0"
# Interfaz opcional:
python -m pip install "calendar-studio[studio]==0.1.0"
calendar-studio studio
```

La primera publicación se realiza desde el workflow de GitHub una vez configurado el Trusted Publisher de PyPI. La existencia de una release de GitHub no confirma por sí sola disponibilidad en PyPI.

## Desde cero

```python
from calendar_studio import CalendarStudio, CalendarSpec, load_holidays

spec = CalendarSpec(
    name="operaciones",
    timezone="America/Mexico_City",
    weekmask=["Mon", "Tue", "Wed", "Thu", "Fri"],
    rules=[
        dict(type="monthly_event", name="cobro", days=[15, 30],
             missing_day="month_end", adjustment="preceding"),
        dict(type="monthly_event", name="pago", days=[17], adjustment="following"),
        dict(type="month_boundary", name="primer_habil", edge="first"),
        dict(type="business_offsets", events=["cobro", "pago"], before=10, after=10),
    ],
)

holidays = load_holidays("festivos.csv", date_col="fecha")
calendar = CalendarStudio(spec).generate(
    start="2026-01-01", end="2026-12-31", holidays=holidays
)
calendar.validate().raise_for_errors()
calendar.export("calendario.parquet")
calendar.save("artefactos/operaciones_2026")
```

`holidays=[]` declara deliberadamente un calendario sin festivos. `None`, archivos ausentes, fechas inválidas/duplicadas, horas y timestamps con zona se rechazan. Las fechas son fechas locales civiles; `timezone` registra el contexto, no convierte automáticamente timestamps ni crea horarios intradía.

Los festivos son exactamente los proporcionados por el usuario. El motor no descarga ni certifica listas oficiales y no deduce que un año esté completo porque haya algunas fechas. Para offsets cerca de los bordes también hay que proporcionar los festivos del contexto relevante.

## Contratos y gramática

`CalendarSpec` es un modelo Pydantic con campos desconocidos prohibidos:

| Campo | Significado |
|---|---|
| `name` | Identificador del calendario. |
| `profile` | `generic` o `mac_legacy_v1`. |
| `timezone` | Zona IANA válida, por defecto UTC. |
| `date_col` | Nombre de la columna de fechas; `date` en el perfil genérico. |
| `weekmask` | Días hábiles posibles, lista no vacía y sin repetidos de Mon…Sun. |
| `rules` | Reglas declarativas validadas por su discriminador `type`. |
| `context_years` | Contexto de cálculo genérico antes/después; 2 por defecto, entre 1 y 10. |

| Regla | Parámetros |
|---|---|
| `monthly_event` | `name`, `days` (1…31), `missing_day`: month_end/skip/raise; `adjustment`: preceding/following/none. |
| `month_boundary` | `name`, `edge`: first/last día hábil del mes. |
| `business_offsets` | `events`, `before`, `after` (0…366 días hábiles). Salidas: `<evento>__before_<k>` y `<evento>__after_<k>`. |

Las banderas son independientes; los solapamientos son válidos. Las reglas se ejecutan por dependencias, no por posición accidental de la configuración. Se rechazan dependencias ausentes/cíclicas, nombres duplicados y resultados desalineados o no binarios.

El perfil genérico genera variables de día, weekday, mes, fin de semana, festivo y día hábil, además de las reglas. El contexto se calcula antes de recortar el rango solicitado para conservar offsets y eventos que cruzan años. Si no alcanza el contexto hábil se rechaza el cálculo, en lugar de inventar banderas.

## Perfiles y compatibilidad

```python
from calendar_studio import CalendarStudio, example_holidays

# Fixture versionado de este proyecto, no un servicio de festivos oficiales.
holidays = example_holidays("mac_legacy_v1")
calendar = CalendarStudio.from_profile("mac_legacy_v1").generate(
    start="2022-01-01", end="2027-12-31", holidays=holidays
)
full = calendar.to_pandas()                 # fecha + 245 banderas
business = calendar.view("business")      # Todas las banderas, sólo fechas hábiles
mac = calendar.view("mac_legacy_v1")      # fecha + 243 banderas, sólo fechas hábiles
mac.export("calendario_mac.parquet")
```

El fixture incluye la corrección `2026-11-02`. Sus fechas actuales llegan hasta `2027-01-01`; no constituye una lista completa de festivos de 2027. Mantén la lista de insumos para el rango que utilices.

El perfil `mac_legacy_v1` conserva el contrato histórico, el orden y la semántica de sus 245 variables. No permite cambiar reglas/weekmask a escondidas; para reglas nuevas usa el perfil genérico. Conserva también particularidades históricas: las columnas llamadas `día par/impar del mes` codifican paridad del **mes**, y las banderas de inicio/cierre de período señalan sus meses, no sólo un día. El motor legado calcula años completos solicitados y conserva sus offsets truncados en los bordes de esos años. El perfil genérico usa contexto extendido. Son políticas explícitamente distintas.

Con los mismos festivos históricos, la vista MAC se comprobó equivalente al calendario anterior del Observatorio: 1,518 fechas × 243 variables sin diferencias. Al añadir `2026-11-02` quedan 1,517 fechas y se recalculan las banderas afectadas. La corrección no se aplica retrospectivamente a corridas entrenadas con otro snapshot.

**Esta versión no modifica ni integra Model Arena.** La vista MAC es sólo una salida disponible para una integración posterior.

## Artefactos

```python
from calendar_studio import CalendarArtifact
loaded = CalendarArtifact.load("artefactos/operaciones_2026")
df = loaded.to_pandas()
print(loaded.metadata)
```

Cada carpeta contiene `calendar.parquet` (Zstandard) y `manifest.json`: configuración, rango, reglas custom declaradas, festivos, eje hábil, esquema, versión y hash SHA-256 de los datos. No se sobrescriben carpetas existentes. La carga verifica el hash, esquema y contrato. Los hashes detectan alteración accidental; no son firmas digitales ni certifican la corrección de los insumos.

La validación inspecciona fechas ordenadas/únicas, cobertura del eje y columnas enteras binarias sin nulos. No rellena columnas faltantes ni convierte valores inválidos para aparentar validez. Las exportaciones devuelven copias y escriben mediante reemplazo atómico.

## Reglas propias

Implementa `CalendarRule`: declara `outputs`, `requires`, `describe()` con configuración/versionado JSON y `apply(CalendarContext)` que devuelve un DataFrame alineado de banderas enteras 0/1. Pasa las instancias con `CalendarStudio(spec, rules=[mi_regla])`. Los artefactos guardan su descripción; cargarlos para lectura no importa ni ejecuta plugins dinámicamente.

## CLI

```bash
calendar-studio generate --start 2026-01-01 --end 2026-12-31 \
  --holidays festivos.csv --holiday-date-col fecha --output artefactos/calendario
```

Usa `--spec configuracion.json` para reglas personalizadas o `--profile mac_legacy_v1`. Studio es una interfaz de generación, consulta y descarga sobre la misma API. La aplicación original `streamlit_app.py` se conserva en el repositorio por compatibilidad; no es el motor público de la librería.

## Desarrollo y pruebas

```bash
python -m pip install -e '.[dev,studio]'
python -m pytest -q
python -m ruff check src/calendar_studio --exclude _legacy.py
python -m build
python -m twine check dist/*
```

Las pruebas originales se conservan como referencia independiente. La suite adicional cubre la corrección de noviembre, años bisiestos, desplazamientos y offsets entre años, weekmasks, contratos negativos, extensibilidad, persistencia, CLI e interfaz opcional. CI ejecuta Python 3.11/3.12 y vuelve a probar el wheel instalado sin importar el paquete desde las fuentes.
