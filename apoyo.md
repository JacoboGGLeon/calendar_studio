Va. Lo que estás construyendo es, en esencia, un **editor de calendario con reglas derivadas**, donde:

* **Default** = determinístico (reglas duras)
* **Eventos** = editables por humano (anclas)
* **Hábiles + reglas laborales** = derivado (depende de fin de semana + festivos)
* **Offsets** = derivado (depende de eventos + N)

Y la clave (correcta) es tu punto central: **“hábil” depende de eventos** (festivos), y a su vez reglas laborales dependen de hábiles. Entonces necesitas una app con pipeline por etapas y recalculo controlado.

Aquí tienes un diseño de proyecto que es robusto y escalable (años 2022–2027, luego otras geografías).

---

# 1) Contrato de datos (el CSV es tu base de persistencia)

## 1.1 Columna ID (inmutable)

* `fecha` (YYYY-MM-DD) **es el primary key**

## 1.2 Capas de columnas (importante)

**Capa A — default (determinísticas, se generan siempre)**

* día del mes (1..31, par/impar)
* día de semana (lunes..domingo, fin_de_semana)
* mes (enero..diciembre)
* agregados (bimestre/trimestre/cuatrimestre/semestre/anual)
* inicios/cierres de periodos (inicio/cierre de cada bloque)

**Capa B — eventos atómicos (editables por humano)**

* `dia_festivo`
* `dia_pago_impuestos`
* `dia_cobro_quincena`
* (y futuras: “cierre contable”, “pago nómina”, etc.)

**Capa C — derivadas por reglas**

* `es_habil`  (depende de NO fin_de_semana y NO festivo)
* reglas laborales:

  * `primer_dia_habil_mes_impar`
  * `ultimo_dia_habil_mes_impar`
  * `primer_dia_habil_mes_par`
  * `ultimo_dia_habil_mes_par`
* offsets por evento:

  * `k_dias_antes_de_EVENTO` para k=1..N
  * `k_dias_despues_de_EVENTO` para k=1..N

👉 Esto te permite recomputar C cada vez que cambie B, sin tocar A.

---

# 2) Pipeline de cómputo (lo que corre la app)

### Paso 0 — Build base (si no existe CSV o si cambia rango)

**Input:** year_min, year_max
**Output:** dataframe con todas las fechas y **Capa A** llena.

### Paso 1 — Eventos (edición humana)

El usuario marca eventos en días específicos (Capa B).

### Paso 2 — Recalcular hábiles

`es_habil = (not fin_de_semana) and (not dia_festivo)`

### Paso 3 — Reglas laborales (dependen de `es_habil`)

Para cada mes:

* si mes impar:

  * primer hábil = primer `fecha` del mes con `es_habil==1`
  * último hábil = último `fecha` del mes con `es_habil==1`
* si mes par: lo mismo, pero guardado en las columnas par

### Paso 4 — Offsets (dependen de eventos + N)

Para cada evento E:

* Si `fecha` es evento (E=1), entonces para k=1..N:

  * marcar `fecha-k` en `k_dias_antes_de_E`
  * marcar `fecha+k` en `k_dias_despues_de_E`

⚠️ Importante: offsets se recomputan **después** de que el usuario edita eventos y después de “recalcular hábiles” (porque tus eventos impactan hábiles, pero offsets no necesariamente dependen de hábil; aún así conviene recalcularlos junto con todo el bloque C).

---

# 3) UI Streamlit (notebook-friendly) — layout 60/40

## Barra superior (global)

* `year_min` slider/select (default 2022)
* `year_max` slider/select (default 2026/2027)
* `offset_N` slider (1..10)
* botones:

  * **“Generar base”** (A)
  * **“Guardar”** (persist)
  * **“Recalcular hábiles + reglas + offsets”** (C completo)

## Cuerpo: Tabs por año

* `st.tabs([2022, 2023, 2024, 2025, 2026, 2027])`

Dentro de cada tab:

### Columna izquierda (60%) — Calendario anual

* Vista tipo calendario (12 meses) o, MVP, vista mensual seleccionable
* Colores:

  * fin de semana → gris claro
  * no hábil por festivo → gris más fuerte (o rojo tenue)
  * eventos → colores por leyenda
  * offsets → gradiente suave del color del evento (opcional)
* Clic sobre un día = selecciona `fecha` (ID) y lo manda al editor

### Columna derecha (40%) — Editor (leyenda + día seleccionado)

**Leyenda / Event Manager**

* tabla de eventos configurados: nombre, color, símbolo, enabled
* botones:

  * “Agregar evento”
  * “Eliminar evento”
  * toggles on/off para mostrar o para “aplicar” en cálculo
* offset_N global + (opcional) override por evento

**Editor de día (fecha seleccionada)**

* muestra resumen default: weekday, mes, etc.
* checkboxes para eventos atómicos:

  * `dia_festivo`
  * `dia_pago_impuestos`
  * `dia_cobro_quincena`
* botón “Aplicar cambios” (escribe sobre df y guarda)

---

# 4) Persistencia (la parte crítica para robustez)

### Archivos recomendados

* `calendar_<year_min>_<year_max>.csv` (tu dataset principal)
* `calendar_meta.json` (config: offset_N, definición de eventos, colores, etc.)
* (opcional) `calendar_audit.log` (cada cambio manual)

### Regla de oro

* **Cada vez que el usuario aplica un cambio** en un día:

  1. actualizas dataframe en memoria
  2. persist CSV (write atomic: escribir temp y renombrar)
  3. marcas un flag “dirty_derivatives = True” si cambió algún evento

Así evitas perder trabajo.

---

# 5) Algoritmos (sin humo, para que sea sólido)

## 5.1 `es_habil`

* `fin_de_semana = (weekday in [5,6])`
* `dia_festivo` viene del usuario
* `es_habil = (not fin_de_semana) and (not dia_festivo)`

## 5.2 Primer/último hábil de mes (par/impar)

Para cada (año, mes):

* `mask = (year==Y & month==M)`
* `candidates = df[mask & (es_habil==1)]`
* si no hay candidates, todo 0 (y quizá warning)
* `first = candidates.fecha.min()`
* `last  = candidates.fecha.max()`
* si M es impar: marca columnas *_mes_impar, si M es par: *_mes_par

## 5.3 Offsets ±N

Para cada evento E:

* `event_dates = df[df[E]==1].fecha`
* para cada d en event_dates y para k in 1..N:

  * `df.loc[df.fecha==d-k, f"{k}_dias_antes_de_{E}"]=1`
  * `df.loc[df.fecha==d+k, f"{k}_dias_despues_de_{E}"]=1`
* importante: antes de recalcular, **resetea a 0** todas las columnas offset del evento, para no acumular basura.

---

# 6) Estructura de proyecto (mínimo pero “pro”)

En vez de un notebook con 2000 líneas, haz esto:

```
calendar_app/
  app.ipynb                  <- notebook que corre streamlit (o que lanza)
  streamlit_app.py           <- entrypoint
  calendar_engine.py         <- build_base, compute_business_days, compute_rules, compute_offsets
  storage.py                 <- load/save atomic, meta json
  ui_components.py           <- calendar grid, legend editor, day editor
  schemas.py                 <- (opcional) pydantic models para config/meta
  data/
    calendar_2022_2027.csv
    calendar_meta.json
```

En notebook: solo importas y corres.

---

# 7) Comportamiento clave (para tu dependencia circular)

No hay circularidad real si lo modelas por **capas**:

* El usuario edita **eventos atómicos**
* Eso cambia `dia_festivo` ⇒ cambia `es_habil`
* Eso cambia reglas laborales (primer/último hábil)
* Luego offsets (dependen solo de eventos y N)

Tu botón “Recalcular…” corre **en orden**:

1. `compute_business_days`
2. `compute_labor_rules`
3. `compute_offsets`

Y listo.

---

# 8) MVP realista (para terminar tu 2026–2027 rápido)

1. Generar base (A) para 2022–2027
2. Vista mensual (no anual completo todavía) + selector de mes
3. Editor de día con checkboxes de eventos atómicos
4. Botón “Recalcular hábiles + reglas + offsets”
5. Export CSV

Luego mejoras:

* vista anual 12 meses
* gradientes de offsets
* reglas por geografía (festivos por país)
* plantillas de eventos (cargar “México fiscal”, etc.)

---

Si quieres, el siguiente paso útil (y ya accionable) es que te entregue **el esqueleto de `calendar_engine.py` + `streamlit_app.py`** con:

* funciones puras (pandas)
* persistencia atómica
* UI 60/40 con tabs por año
* edición de eventos por día

Dímelo y lo genero directo (en un solo bloque de código listo para copiar a tu repo).
