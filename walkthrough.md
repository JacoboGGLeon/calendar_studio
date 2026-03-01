# Walkthrough - 2026 Calendar Application

The **Calendar Studio** has been built using Streamlit, offering a premium dark-themed interface to manage your 2026 calendar.

## 🚀 How to Run

### Option 1: Local Execution
Run the app directly with Streamlit:
```bash
streamlit run streamlit_app.py
```
Then open `http://localhost:8501` in your browser.

### Option 2: Google Colab
Use the provided runner script which sets up tunneling:
```bash
python run_colab_experiment.py
```

## ✨ Features

### 📅 Interactive Calendar (Left Panel)
- **Visual Grid**: A monthly view of the year 2026.
- **Navigation**: Use the Sidebar to switch between Year/Month.
- **Holidays**: Days with "dia festivo" are marked with a red dot (🔴).
- **Selection**: Click any day button to select it.

### 🔎 Day Inspector (Right Panel)
- **Details**: Shows the selected date and its Row ID from the CSV.
- **Active Tags**: Lists all boolean flags currently active for that day (e.g., `inicio del ano`, `dia de pago`).
- **Editor**:
    - Search for any tag (out of ~246 columns) in the search bar.
    - Toggle the checkbox to set/unset the tag.
    - Click **"Save Changes"** to write back to `calendario_2026.csv`.

## 📂 Data Management
- The app attempts to load `calendario_2026.csv`.
- If missing, it generates a default dataset.
- Use **"Reset / Reload Data"** in the sidebar to refresh from disk.
