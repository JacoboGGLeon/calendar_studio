# Algoritmo de Lógica de Calendario (Motor de Reglas)

Este documento describe el algoritmo utilizado para generar y validar el calendario, basado en una arquitectura de capas (Layers) que permite recalcular reglas de negocio dinámicamente.

## Arquitectura de Capas

El sistema no es una simple base de datos, sino un motor de cómputo secuencial:

1.  **Capa A (Base)**: Estructura de tiempo inmutable.
2.  **Capa B (Eventos)**: Entradas del usuario (Semillas).
3.  **Capa C (Derivados)**: Reglas calculadas automáticamente.

---

## Descripción del Algoritmo

### 1. Construcción Base (Capa A)
Generamos el esqueleto del tiempo. Esto es puramente determinístico.
*   Para cada día del rango (ej. 2022-2027):
    *   Determinamos Año, Mes, Día.
    *   Calculamos si es Fin de Semana (Sábado/Domingo).

### 2. Inyección de Eventos (Capa B)
Aquí entran los datos "humanos" o semillas.
*   Se carga la lista de días marcados como *Eventos* (ej. "Día Festivo", "Pago de Impuestos").
*   Estos son los **únicos** datos que el usuario edita directamente.

### 3. Cálculo de Reglas (Capa C)
Aquí ocurre la magia. Todo lo siguiente se borra y re-calcula si la Capa B cambia.

#### A. Días Hábiles (`es_habil`)
Un día es hábil si cumple dos condiciones negativas:
1.  NO es fin de semana.
2.  NO es un día festivo (según Capa B).

#### B. Offsets (Días Antes/Después)
Para cada tipo de evento (ej. "Festivo"), calculamos sus "sombras" o recordatorios (offsets) de 1 a 10 días antes y después.

**Regla de Supresión (Clave para exactitud):**
Si un día $D$ debería ser marcado como "1 día antes de Festivo", pero el día $D$ **ya es un Festivo** en sí mismo, **NO** se marca el offset.
*   *Lógica*: No tiene sentido avisar "mañana es festivo" si hoy ya estamos en festivo (o la regla de negocio implica que el offset se absorbe).

---

## Pseudocódigo

```python
FUNCION GenerarCalendario(año_inicio, año_fin, lista_eventos_usuario):

    # --- PASO 1: CAPA A (Base) ---
    PARA cada fecha D desde (año_inicio-01-01) hasta (año_fin-12-31):
        Crear Registro(D)
        Registro(D).fin_de_semana = (D es Sábado O D es Domingo)
    
    # --- PASO 2: CAPA B (Semillas) ---
    PARA cada evento E en lista_eventos_usuario:
        Marcar Registro(E.fecha).es_evento[E.tipo] = VERDADERO
    
    # --- PASO 3: CAPA C (Lógica Derivada) ---
    
    # C1: Días Hábiles
    PARA cada fecha D:
        SI (Registro(D).fin_de_semana ES FALSO) Y (Registro(D).es_evento['Festivo'] ES FALSO):
            Registro(D).es_habil = VERDADERO
        SINO:
            Registro(D).es_habil = FALSO

    # C2: Offsets con Supresión
    PARA cada TipoEvento T (ej. 'Festivo'):
        # Buscar todas las fechas semillas
        FechasSemilla = Buscar(Donde es_evento[T] ES VERDADERO)
        
        PARA cada FechaSemilla FS en FechasSemilla:
            PARA k desde 1 hasta 10:
                
                # Calcular Offset Antes (FS - k días)
                FechaObjetivo = FS - k días
                
                # REGLA DE SUPRESIÓN:
                # Solo marcar si la FechaObjetivo NO es también un evento T
                SI Registro(FechaObjetivo).es_evento[T] ES FALSO:
                    Registro(FechaObjetivo).offset_antes[k] = VERDADERO
                
                # (Lo mismo aplica para días después)
                FechaObjetivo = FS + k días
                SI Registro(FechaObjetivo).es_evento[T] ES FALSO:
                    Registro(FechaObjetivo).offset_despues[k] = VERDADERO

    RETORNAR CalendarioCompleto
```
