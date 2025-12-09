"""
Entry point for the GUI.

This file is what `parsingtool-gui` points at.
"""

import sys
import os
from ParsingTool.parsing.gui import run_gui  # adjust if your GUI file name is different


def main() -> None:
    # Check if running as a PyInstaller Bundle
    if getattr(sys, 'frozen', False):
        # PyInstaller unpacks the exe to a temp folder at sys._MEIPASS
        base_path = sys._MEIPASS
        
        # Define paths to our bundled tools
        # These folder names must match the --add-data flags in the build command
        tesseract_path = os.path.join(base_path, 'tesseract')
        
        # Check standard poppler structure
        poppler_path = os.path.join(base_path, 'poppler', 'Library', 'bin')
        if not os.path.exists(poppler_path):
             poppler_path = os.path.join(base_path, 'poppler', 'bin')
            
        # Add to System PATH
        os.environ["PATH"] += os.pathsep + tesseract_path
        os.environ["PATH"] += os.pathsep + poppler_path
        
        # Set Tesseract data path
        os.environ["TESSDATA_PREFIX"] = os.path.join(tesseract_path, 'tessdata')

    run_gui()


if __name__ == "__main__":
    main()
