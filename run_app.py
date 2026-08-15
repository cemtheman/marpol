import os
import sys
import webbrowser
from threading import Timer
import streamlit.web.cli as stcli

def open_browser():
    """Uygulama başladığında varsayılan tarayıcıyı otomatik açar."""
    webbrowser.open_new('http://localhost:8501')

def main():
    # PyInstaller ile paketlendiğinde geçici klasör yolunu tespit eder
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    script_path = os.path.join(base_dir, 'marpol.py')
    
    # 1.5 saniye sonra tarayıcıyı aç
    Timer(1.5, open_browser).start()

    # Streamlit CLI'yi tetikle
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]
    sys.exit(stcli.main())

if __name__ == '__main__':
    main()
