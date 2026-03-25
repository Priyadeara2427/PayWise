# test_environment.py
import sys
print(f"Python version: {sys.version}")

# Test critical imports
try:
    import numpy as np
    print(f"✓ NumPy {np.__version__}")
    
    import pandas as pd
    print(f"✓ Pandas {pd.__version__}")
    
    import pytesseract
    print(f"✓ pytesseract {pytesseract.__version__}")
    
    import cv2
    print(f"✓ OpenCV {cv2.__version__}")
    
    import fitz
    print(f"✓ PyMuPDF")
    
    import pdfplumber
    print(f"✓ pdfplumber {pdfplumber.__version__}")
    
    print("\n✅ All dependencies are ready!")
    
except ImportError as e:
    print(f"❌ Missing dependency: {e}")