# Implementation Plan: 2026 Calendar Studio (Rule-Based Engine)

This plan implements the architecture defined in `apoyo.md`, transitioning from a simple visualizer to a robust **Derived Rules Engine**.

> [!IMPORTANT]
> **Core Philosophy**:
> 1. **Layer A (Default)**: Deterministic calendar structure (Year, Month, Day, Weekday).
> 2. **Layer B (Events)**: Atomic User Inputs (Holidays, Tax Days).
> 3. **Layer C (Derived)**: Business Days & Offsets. Recalculated ONLY when Layer B changes.

## 1. Core Engine (`src/calendar_engine.py`)
Encapsulates the logic pipeline.

- **`build_base_calendar(year_min, year_max)`**: Generates Layer A.
- **`compute_business_days(df)`**: Layer C1. `es_habil = not (weekend or events)`.
- **`compute_labor_rules(df)`**: Layer C2. Identifies First/Last business days of periods.
- **`compute_offsets(df, events, N)`**: Layer C3. Marks ±N days around events.

## 2. Storage & Persistence (`src/storage.py`)
Handles data integrity.

- **`load_data()`**: Loads CSV + Meta JSON.
- **`save_data_atomic(df)`**: Writes to temp, then renames to ensure no data corruption.
- **`load_meta()` / `save_meta()`**: Manages Event definitions (Name, Color, Enabled status).

## 3. Application UI (`streamlit_app.py`)
Adopts the **60/40 Layout** with Annual Tabs.

### Layout
- **Global Header**: Year Range Selector, "Recalculate" Button (triggers pipeline).
- **Tabs**: `[2022, 2023, ..., 2027]`
- **Split View**:
    - **Left (60%)**: **Annual Calendar View**.
        - Instead of 1 month, we show a full year grid (or efficient 12-month grid).
        - Color-coded by events.
    - **Right (40%)**: **Event Manager & Day Editor**.
        - **Legend**: List of defined events (e.g., "Festivo", "Nomina").
        - **Day Details**: When a day is clicked (in Left col), show details here.
        - **Atomic Toggles**: Checkboxes for Layer B input.

## Verification
- **Pipeline Test**: Mark a day as "Festivo" -> Run Recalculate -> Verify `es_habil` becomes 0 -> Verify "1 day before" offset appears.
- **Persistence Test**: Save, Restart App, Verify changes persist.
- **UI Test**: Navigate years via tabs.
