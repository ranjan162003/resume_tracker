"""Starts the Streamlit dashboard.

Usage: python run_dashboard.py
"""
import subprocess
import sys

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app/dashboard/streamlit_app.py"])
