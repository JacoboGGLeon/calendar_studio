import os
import pandas as pd


# ---------------------------------------------------------------------------
# Calendar Studio Engine
# ---------------------------------------------------------------------------
# Regla madre:
# 1) Los festivos vienen de festivos.csv.
# 2) Los fines de semana se calculan por fecha.
# 3) Día hábil = NO festivo y NO fin de semana.
# 4) Todas las reglas derivadas usan solamente días hábiles.
#
# Contrato de salida:
# - El calendario exportado debe respetar el layout histórico del archivo
#   "calendario_mayo_2026_enteros.csv".
# - Las columnas auxiliares de cálculo pueden existir internamente, pero no
#   deben salir en el CSV final.


AUXILIARY_COLUMNS = ["año", "mes", "dia", "weekday", "es_habil"]


def required_output_columns():
    """Return the exact column order required by downstream programs."""
    cols = ["fecha"]

    cols += [f"día {i}" for i in range(1, 32)]

    cols += [
        "día lunes",
        "día martes",
        "día miércoles",
        "día jueves",
        "día viernes",
        "fin de semana",
    ]

    cols += [
        "mes de enero",
        "mes de febrero",
        "mes de marzo",
        "mes de abril",
        "mes de mayo",
        "mes de junio",
        "mes de julio",
        "mes de agosto",
        "mes de septiembre",
        "mes de octubre",
        "mes de noviembre",
        "mes de diciembre",
    ]

    cols += [f"bimestre {i} del año" for i in range(1, 7)]
    cols += [f"trimestre {i} del año" for i in range(1, 5)]
    cols += [f"cuatrimestre {i} del año" for i in range(1, 4)]
    cols += [f"semestre {i} del año" for i in range(1, 3)]

    cols += [
        "inicio del bimestre contable 1",
        "inicio del bimestre contable 2",
        "inicio del bimestre contable 3",
        "inicio del bimestre 4",
        "inicio del bimestre 5",
        "inicio del bimestre 6",
        "inicio del trimestre 1",
        "inicio del trimestre 2",
        "inicio del trimestre 3",
        "inicio del trimestre 4",
        "inicio del cuatrimestre 1",
        "inicio del cuatrimestre 2",
        "inicio del cuatrimestre 3",
        "inicio del semestre 1",
        "inicio del semestre 2",
        "inicio del anual",
        "cierre del bimestre 1",
        "cierre del bimestre 2",
        "cierre del bimestre 3",
        "cierre del bimestre 4",
        "cierre del bimestre 5",
        "cierre del bimestre 6",
        "cierre del trimestre 1",
        "cierre del trimestre 2",
        "cierre del trimestre 3",
        "cierre del trimestre 4",
        "cierre del cuatrimestre 1",
        "cierre del cuatrimestre 2",
        "cierre del cuatrimestre 3",
        "cierre del semestre 1",
        "cierre del semestre 2",
        "cierre del anual",
        "día par del mes",
        "día impar del mes",
    ]

    offset_events = [
        "día de pago de impuestos",
        "día de cobro de quincena",
        "día festivo",
        "primer día hábil de mes impar",
        "último día hábil de mes impar",
        "primer día hábil de mes par",
        "último día hábil de mes par",
    ]

    for event_col in offset_events:
        cols += [f"{k} días antes de {event_col}" for k in range(10, 0, -1)]
        cols += [event_col]
        cols += [f"{k} días después de {event_col}" for k in range(1, 11)]

    return cols


# --- FUNCIONES AUXILIARES DE SALTO (LEAP) ---


def backward_leap_to_habil(df, target_days):
    """
    Given target days, mark the closest previous business day.

    The target itself is allowed when it is already a business day.
    """
    res = pd.Series(0, index=df.index, dtype="int64")
    if isinstance(target_days, pd.Series):
        target_idxs = df.index[target_days].tolist()
    else:
        target_idxs = target_days

    for idx in target_idxs:
        curr_idx = idx
        while curr_idx >= 0 and df.at[curr_idx, "es_habil"] == 0:
            curr_idx -= 1
        if curr_idx >= 0:
            res.at[curr_idx] = 1
    return res


def forward_leap_to_habil(df, target_days):
    """
    Given target days, mark the closest following business day.

    The target itself is allowed when it is already a business day.
    """
    res = pd.Series(0, index=df.index, dtype="int64")
    if isinstance(target_days, pd.Series):
        target_idxs = df.index[target_days].tolist()
    else:
        target_idxs = target_days

    max_idx = len(df) - 1
    for idx in target_idxs:
        curr_idx = idx
        while curr_idx <= max_idx and df.at[curr_idx, "es_habil"] == 0:
            curr_idx += 1
        if curr_idx <= max_idx:
            res.at[curr_idx] = 1
    return res


# --- FUNCIONES DE OFFSET ---


def compute_working_offset_backward(df, col, k):
    """Mark the k-th previous business day before each event in col."""
    res = pd.Series(0, index=df.index, dtype="int64")
    event_idxs = df.index[df[col] == 1].tolist()

    for idx in event_idxs:
        steps = 0
        curr_idx = idx

        while steps < k and curr_idx > 0:
            curr_idx -= 1
            if df.at[curr_idx, "es_habil"] == 1:
                steps += 1

        # Flags are independent: an offset may land on a date that is also
        # the original event or another flag. Do not suppress overlaps.
        if steps == k:
            res.at[curr_idx] = 1

    return res


def compute_working_offset_forward(df, col, k):
    """Mark the k-th following business day after each event in col."""
    res = pd.Series(0, index=df.index, dtype="int64")
    event_idxs = df.index[df[col] == 1].tolist()
    max_idx = len(df) - 1

    for idx in event_idxs:
        steps = 0
        curr_idx = idx

        while steps < k and curr_idx < max_idx:
            curr_idx += 1
            if df.at[curr_idx, "es_habil"] == 1:
                steps += 1

        # Flags are independent: an offset may land on a date that is also
        # the original event or another flag. Do not suppress overlaps.
        if steps == k:
            res.at[curr_idx] = 1

    return res


# --- ENGINE INTERFACE ---


def build_base_calendar(year_min, year_max):
    """Build primary calendar variables plus auxiliary columns for the engine."""
    dates = pd.date_range(start=f"{year_min}-01-01", end=f"{year_max}-12-31", freq="D")
    df = pd.DataFrame({"fecha": dates})

    # Dummies de días 1 al 31
    for i in range(1, 32):
        df[f"día {i}"] = (df["fecha"].dt.day == i).astype(int)

    # Dummies de día de la semana
    dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes"]
    for i, dia_str in enumerate(dias_semana):
        df[f"día {dia_str}"] = (df["fecha"].dt.weekday == i).astype(int)

    # Fin de semana
    df["fin de semana"] = df["fecha"].dt.weekday.isin([5, 6]).astype(int)

    # Dummies de mes
    meses_nombres = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    for i, mes_str in enumerate(meses_nombres):
        df[f"mes de {mes_str}"] = (df["fecha"].dt.month == (i + 1)).astype(int)

    # Compatibilidad con el layout histórico:
    # "día par/impar del mes" realmente significa mes par/impar.
    df["día par del mes"] = (df["fecha"].dt.month % 2 == 0).astype(int)
    df["día impar del mes"] = (df["fecha"].dt.month % 2 != 0).astype(int)

    # Auxiliares internos
    df["año"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["dia"] = df["fecha"].dt.day
    df["weekday"] = df["fecha"].dt.weekday

    # Periodos
    df["bimestre_num"] = df["fecha"].dt.month.apply(lambda x: (x - 1) // 2 + 1)
    for i in range(1, 7):
        df[f"bimestre {i} del año"] = (df["bimestre_num"] == i).astype(int)

    df["trimestre_num"] = df["fecha"].dt.month.apply(lambda x: (x - 1) // 3 + 1)
    for i in range(1, 5):
        df[f"trimestre {i} del año"] = (df["trimestre_num"] == i).astype(int)

    df["cuatrimestre_num"] = df["fecha"].dt.month.apply(lambda x: (x - 1) // 4 + 1)
    for i in range(1, 4):
        df[f"cuatrimestre {i} del año"] = (df["cuatrimestre_num"] == i).astype(int)

    df["semestre_num"] = df["fecha"].dt.month.apply(lambda x: (x - 1) // 6 + 1)
    for i in range(1, 3):
        df[f"semestre {i} del año"] = (df["semestre_num"] == i).astype(int)

    period_months = {
        "bimestre": {1: (1, 2), 2: (3, 4), 3: (5, 6), 4: (7, 8), 5: (9, 10), 6: (11, 12)},
        "trimestre": {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)},
        "cuatrimestre": {1: (1, 4), 2: (5, 8), 3: (9, 12)},
        "semestre": {1: (1, 6), 2: (7, 12)},
    }

    nuevas_columnas_periodo = {}
    for period_str, num_col in [
        ("bimestre", "bimestre_num"),
        ("trimestre", "trimestre_num"),
        ("cuatrimestre", "cuatrimestre_num"),
        ("semestre", "semestre_num"),
    ]:
        for i in sorted(df[num_col].dropna().unique()):
            if period_str == "bimestre" and i <= 3:
                inicio_col = f"inicio del {period_str} contable {i}"
            else:
                inicio_col = f"inicio del {period_str} {i}"

            cierre_col = f"cierre del {period_str} {i}"

            i_month, c_month = period_months[period_str][int(i)]
            nuevas_columnas_periodo[inicio_col] = (
                (df["fecha"].dt.month == i_month) & (df[num_col] == i)
            ).astype(int)
            nuevas_columnas_periodo[cierre_col] = (
                (df["fecha"].dt.month == c_month) & (df[num_col] == i)
            ).astype(int)

    nuevas_columnas_periodo["inicio del anual"] = (df["fecha"].dt.month == 1).astype(int)
    nuevas_columnas_periodo["cierre del anual"] = (df["fecha"].dt.month == 12).astype(int)

    df = pd.concat([df, pd.DataFrame(nuevas_columnas_periodo)], axis=1)
    df = df.drop(columns=["bimestre_num", "trimestre_num", "cuatrimestre_num", "semestre_num"])

    return df


def _ensure_internal_columns(df):
    """Ensure engine auxiliary columns exist after loading an export-layout CSV."""
    df = df.copy()

    df["fecha"] = pd.to_datetime(df["fecha"])

    if "año" not in df.columns:
        df["año"] = df["fecha"].dt.year
    if "mes" not in df.columns:
        df["mes"] = df["fecha"].dt.month
    if "dia" not in df.columns:
        df["dia"] = df["fecha"].dt.day
    if "weekday" not in df.columns:
        df["weekday"] = df["fecha"].dt.weekday

    if "fin de semana" not in df.columns:
        df["fin de semana"] = df["fecha"].dt.weekday.isin([5, 6]).astype(int)

    return df


def _load_holidays_from_csv(path="festivos.csv"):
    """Load holidays from the single manual source of truth."""
    if not os.path.exists(path):
        return set()

    fest_df = pd.read_csv(path)
    if "fecha" not in fest_df.columns:
        raise ValueError(f"{path} debe contener una columna 'fecha'.")

    return set(pd.to_datetime(fest_df["fecha"]).dt.strftime("%Y-%m-%d"))


def _apply_holiday_and_business_day_rules(df, holidays_path="festivos.csv"):
    """Apply the non-negotiable order: holidays, weekends, business days."""
    df = _ensure_internal_columns(df)

    holidays = _load_holidays_from_csv(holidays_path)
    if holidays:
        df["día festivo"] = df["fecha"].dt.strftime("%Y-%m-%d").isin(holidays).astype(int)
    elif "día festivo" not in df.columns:
        df["día festivo"] = 0

    df["fin de semana"] = df["fecha"].dt.weekday.isin([5, 6]).astype(int)
    df["es_habil"] = ((df["fin de semana"] == 0) & (df["día festivo"] == 0)).astype(int)

    return df


def _mark_quincenas(df):
    """
    Mark quincenas using the business rule:
    - first quincena: day 15, or closest previous business day;
    - second quincena: theoretical day 30, or closest previous business day;
    - months without day 30, e.g. February, use the real last day of month.
    """
    max_day_by_month = df.groupby(["año", "mes"])["dia"].transform("max")
    second_target_day = max_day_by_month.clip(upper=30)

    target_quincenas = (df["dia"] == 15) | (df["dia"] == second_target_day)
    df["día de cobro de quincena"] = backward_leap_to_habil(df, target_quincenas)

    return df


def _mark_impuestos(df):
    """Mark taxes on day 17, or closest following business day."""
    target_impuestos = df["dia"] == 17
    df["día de pago de impuestos"] = forward_leap_to_habil(df, target_impuestos)
    return df


def _mark_first_last_business_days(df):
    """Mark first/last business day of odd/even months."""
    df["primer día hábil de mes impar"] = 0
    df["último día hábil de mes impar"] = 0
    df["primer día hábil de mes par"] = 0
    df["último día hábil de mes par"] = 0

    habil_df = df[df["es_habil"] == 1]
    if habil_df.empty:
        return df

    primeros = habil_df.groupby(["año", "mes"])["fecha"].idxmin()
    ultimos = habil_df.groupby(["año", "mes"])["fecha"].idxmax()

    primeros_impar = primeros[primeros.index.get_level_values("mes") % 2 != 0].values
    primeros_par = primeros[primeros.index.get_level_values("mes") % 2 == 0].values

    ultimos_impar = ultimos[ultimos.index.get_level_values("mes") % 2 != 0].values
    ultimos_par = ultimos[ultimos.index.get_level_values("mes") % 2 == 0].values

    df.loc[primeros_impar, "primer día hábil de mes impar"] = 1
    df.loc[ultimos_impar, "último día hábil de mes impar"] = 1
    df.loc[primeros_par, "primer día hábil de mes par"] = 1
    df.loc[ultimos_par, "último día hábil de mes par"] = 1

    return df


def _mark_offsets(df):
    """Create ±10 business-day offsets for all contractual event columns."""
    eventos_con_offset = [
        "día de pago de impuestos",
        "día de cobro de quincena",
        "día festivo",
        "primer día hábil de mes impar",
        "último día hábil de mes impar",
        "primer día hábil de mes par",
        "último día hábil de mes par",
    ]

    n = 10
    offset_cols = {}

    for event_col in eventos_con_offset:
        for k in range(1, n + 1):
            offset_cols[f"{k} días antes de {event_col}"] = compute_working_offset_backward(df, event_col, k)
            offset_cols[f"{k} días después de {event_col}"] = compute_working_offset_forward(df, event_col, k)

    offsets_df = pd.DataFrame(offset_cols, index=df.index)
    return pd.concat([df, offsets_df], axis=1).copy()


def run_recalculation_pipeline(df, event_configs=None, holidays_path="festivos.csv"):
    """
    Execute all domain rules.

    The `event_configs` argument is kept for UI compatibility, but the engine
    intentionally derives contractual events from holidays/business-day logic.
    Manual quincenas.csv and impuestos.csv are not used as rule inputs.
    """
    df = df.copy()
    df = _ensure_internal_columns(df)

    # Remove derived columns before recomputing, avoiding stale flags from prior runs.
    derived_cols = [
        col for col in df.columns
        if (
            col in required_output_columns()
            and (
                "días antes de" in col
                or "días después de" in col
                or col in {
                    "día de pago de impuestos",
                    "día de cobro de quincena",
                    "día festivo",
                    "primer día hábil de mes impar",
                    "último día hábil de mes impar",
                    "primer día hábil de mes par",
                    "último día hábil de mes par",
                }
            )
        )
    ]
    df = df.drop(columns=[col for col in derived_cols if col in df.columns], errors="ignore")

    df = _apply_holiday_and_business_day_rules(df, holidays_path=holidays_path)
    df = _mark_impuestos(df)
    df = _mark_quincenas(df)
    df = _mark_first_last_business_days(df)
    df = _mark_offsets(df)

    return df


def to_required_output_layout(df):
    """
    Return a DataFrame with the exact required export layout and column order.

    Any missing required output column is created as 0. Internal auxiliary
    columns are omitted from this export view.
    """
    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m-%d")

    cols = required_output_columns()
    for col in cols:
        if col not in df.columns:
            df[col] = 0

    out = df[cols].copy()

    for col in cols:
        if col != "fecha":
            out[col] = out[col].fillna(0).astype(int)

    return out


def validate_business_rules(df):
    """
    Return validation diagnostics for the core business rules.
    Useful for tests, notebooks and pre-export checks.
    """
    work = _ensure_internal_columns(df)

    if "día festivo" not in work.columns:
        work["día festivo"] = 0
    if "es_habil" not in work.columns:
        work["es_habil"] = ((work["fin de semana"] == 0) & (work["día festivo"] == 0)).astype(int)

    diagnostics = {
        "rows": int(len(work)),
        "columns_export_layout": int(len(required_output_columns())),
        "quincenas_en_no_habil": [],
        "impuestos_en_no_habil": [],
    }

    if "día de cobro de quincena" in work.columns:
        bad_q = work[
            (work["día de cobro de quincena"] == 1)
            & ((work["fin de semana"] == 1) | (work["día festivo"] == 1))
        ]
        diagnostics["quincenas_en_no_habil"] = bad_q["fecha"].dt.strftime("%Y-%m-%d").tolist()

    if "día de pago de impuestos" in work.columns:
        bad_i = work[
            (work["día de pago de impuestos"] == 1)
            & ((work["fin de semana"] == 1) | (work["día festivo"] == 1))
        ]
        diagnostics["impuestos_en_no_habil"] = bad_i["fecha"].dt.strftime("%Y-%m-%d").tolist()

    return diagnostics


def validate_export_calendar(df, holidays_path="festivos.csv"):
    """
    Validate the generated calendar as a downstream export contract.

    Important business invariant:
    flags are independent. A date may have many columns marked as 1; overlaps
    are valid and expected. Validation must never treat multiple active flags
    on the same date as an error.
    """
    work = df.copy()
    work = _ensure_internal_columns(work)

    year_min = int(work["fecha"].dt.year.min())
    year_max = int(work["fecha"].dt.year.max())

    actual = to_required_output_layout(work)

    expected = build_base_calendar(year_min, year_max)
    expected = run_recalculation_pipeline(expected, holidays_path=holidays_path)
    expected = to_required_output_layout(expected)

    checks = []

    def add_check(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    required_cols = required_output_columns()
    add_check(
        "layout_columns",
        list(actual.columns) == required_cols,
        f"actual={len(actual.columns)} expected={len(required_cols)}",
    )
    add_check("row_count", len(actual) == len(expected), f"actual={len(actual)} expected={len(expected)}")
    add_check("fecha_unique", actual["fecha"].is_unique, "fechas sin duplicados")
    add_check("no_nulls", not actual.isna().any().any(), "sin valores nulos")

    binary_cols = [c for c in actual.columns if c != "fecha"]
    non_binary_cols = [c for c in binary_cols if not actual[c].dropna().isin([0, 1]).all()]
    add_check("binary_flags", not non_binary_cols, ", ".join(non_binary_cols[:10]))

    # Regla madre: fin de semana y festivos generan es_habil internamente.
    actual_dates = pd.to_datetime(actual["fecha"])
    expected_weekend = actual_dates.dt.weekday.isin([5, 6]).astype(int)
    weekend_bad = actual.loc[actual["fin de semana"].astype(int).ne(expected_weekend), "fecha"].tolist()
    add_check("weekend_flags", not weekend_bad, ", ".join(weekend_bad[:10]))

    compare_cols = [c for c in required_cols if c != "fecha"]
    mismatches = {}
    if len(actual) == len(expected):
        for c in compare_cols:
            bad = actual[c].astype(int).ne(expected[c].astype(int))
            if bad.any():
                mismatches[c] = int(bad.sum())
    add_check(
        "derived_rules_match_engine",
        not mismatches,
        "; ".join(f"{k}: {v}" for k, v in list(mismatches.items())[:10]),
    )

    event_cols = [
        "día de pago de impuestos",
        "día de cobro de quincena",
        "día festivo",
        "primer día hábil de mes impar",
        "último día hábil de mes impar",
        "primer día hábil de mes par",
        "último día hábil de mes par",
    ]
    offset_cols = [c for c in actual.columns if "días antes de" in c or "días después de" in c]
    business_rule_cols = [c for c in event_cols + offset_cols if c in actual.columns]
    active_flags_per_date = actual[business_rule_cols].sum(axis=1) if business_rule_cols else pd.Series(0, index=actual.index)

    overlap_count = int((active_flags_per_date > 1).sum())
    max_flags_on_one_date = int(active_flags_per_date.max()) if len(active_flags_per_date) else 0
    add_check(
        "overlapping_flags_allowed",
        True,
        f"fechas_con_multiples_banderas={overlap_count}; max_banderas_en_una_fecha={max_flags_on_one_date}",
    )

    ok = all(item["ok"] for item in checks)
    return {
        "ok": ok,
        "checks": checks,
        "mismatches": mismatches,
        "overlap_count": overlap_count,
        "max_flags_on_one_date": max_flags_on_one_date,
    }
