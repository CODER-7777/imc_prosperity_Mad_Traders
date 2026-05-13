import os
import sys

def try_import(module_name):
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False

# Attempt to install pypdf if nothing is available
if not try_import('fitz') and not try_import('pypdf') and not try_import('PyPDF2'):
    os.system("pip install pypdf")

def extract():
    target = 'Game_Mechanics_Overview_.pdf'
    if not os.path.exists(target):
        print("File not found")
        return
        
    text = ""
    if try_import('fitz'):
        import fitz
        doc = fitz.open(target)
        for page in doc:
            text += page.get_text() + "\n"
    elif try_import('pypdf'):
        import pypdf
        reader = pypdf.PdfReader(target)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif try_import('PyPDF2'):
        import PyPDF2
        reader = PyPDF2.PdfReader(target)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    else:
        print("Failed to get a PDF library")
        return
        
    with open('game_mechanics.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: File extracted to game_mechanics.txt")

extract()
