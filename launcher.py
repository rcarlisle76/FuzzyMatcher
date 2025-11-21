#!/usr/bin/env python3
"""
Fuzzkonnect Launcher
Starts the Flask application and automatically opens it in the default browser
"""

import webbrowser
import time
import threading
import sys
import os
from pathlib import Path

# Set up the application directory
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = sys._MEIPASS
else:
    # Running as script
    application_path = os.path.dirname(os.path.abspath(__file__))

# Change to application directory
os.chdir(application_path)

# Import Flask app
from app import app

# Configuration
HOST = '127.0.0.1'
PORT = 5000
URL = f'http://{HOST}:{PORT}'

def open_browser():
    """Open the default web browser after a short delay"""
    time.sleep(1.5)  # Wait for Flask to start
    try:
        webbrowser.open(URL)
        print(f"\nOpened browser at {URL}")
    except Exception as e:
        print(f"\nCould not open browser automatically: {e}")
        print(f"Please open your browser and navigate to: {URL}")

def run_app():
    """Run the Flask application"""
    print("=" * 60)
    print("  Fuzzkonnect - Field Matching Tool")
    print("  Riskonnect Migration Services")
    print("=" * 60)
    print(f"\nStarting server at {URL}")
    print("\nPress CTRL+C to stop the server")
    print("-" * 60)

    # Start browser opener in background thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Run Flask app
    try:
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        print("Goodbye!")
    except Exception as e:
        print(f"\nError starting server: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    run_app()
