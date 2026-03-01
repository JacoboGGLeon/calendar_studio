import subprocess
import time
import os
import sys

# ---- PARAMS (Colab UI) ----
PORT = 8501
MODE = "window"  # or "iframe"
IFRAME_HEIGHT = 800
IFRAME_WIDTH = "100%"

def run_experiment():
    # ---- Check environment ----
    try:
        from google.colab import output
        _IN_COLAB = True
    except ImportError:
        output = None
        _IN_COLAB = False

    print("🚀 Starting Calendar Studio...")

    # ---- Kill previous ----
    if os.name != 'nt': # posix
        os.system('pkill -f "streamlit run streamlit_app.py" || true')
    
    # ---- Launch Streamlit ----
    cmd = [
        "streamlit", "run", "streamlit_app.py",
        "--server.address", "0.0.0.0",
        "--server.port", str(PORT),
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
    ]

    print(f"Running command: {' '.join(cmd)}")
    
    # Using Popen to run in background
    process = subprocess.Popen(cmd)
    
    print("⏳ Waiting for startup...")
    time.sleep(3)

    # ---- Expose ----
    if _IN_COLAB and output is not None:
        if MODE == "iframe":
            output.serve_kernel_port_as_iframe(
                PORT,
                width=IFRAME_WIDTH,
                height=IFRAME_HEIGHT,
            )
        else:
            output.serve_kernel_port_as_window(
                PORT,
                anchor_text="🔗 Open Calendar Studio"
            )
    else:
        print(f"✅ Streamlit running at http://localhost:{PORT}")
        print("Press Ctrl+C to stop.")
        
    try:
        process.wait()
    except KeyboardInterrupt:
        print("🛑 Stopping...")
        process.terminate()

if __name__ == "__main__":
    run_experiment()
