"""Extract readable text from PDFs using raw binary parsing."""
import re
import sys
import os

def extract_pdf_text(filepath):
    """Extract text from PDF by reading raw stream content."""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Decode as latin-1 to preserve all bytes
    raw = data.decode('latin-1')
    
    # Method 1: Extract text between BT and ET markers (text objects)
    text_blocks = re.findall(r'BT\s*(.*?)\s*ET', raw, re.DOTALL)
    
    all_text = []
    for block in text_blocks:
        # Extract text from Tj and TJ operators
        # Tj: (text) Tj
        tj_matches = re.findall(r'\((.*?)\)\s*Tj', block)
        all_text.extend(tj_matches)
        
        # TJ: [(text) num (text) ...] TJ
        tj_array_matches = re.findall(r'\[(.*?)\]\s*TJ', block, re.DOTALL)
        for arr in tj_array_matches:
            parts = re.findall(r'\((.*?)\)', arr)
            all_text.extend(parts)
    
    # Clean up escape sequences
    cleaned = []
    for t in all_text:
        t = t.replace('\\n', '\n').replace('\\r', '\r')
        t = t.replace('\\(', '(').replace('\\)', ')')
        t = t.replace('\\\\', '\\')
        # Handle octal escapes
        t = re.sub(r'\\(\d{3})', lambda m: chr(int(m.group(1), 8)), t)
        if t.strip():
            cleaned.append(t.strip())
    
    return ' '.join(cleaned)

# Process all PDFs in the docs folder
docs_dir = os.path.dirname(os.path.abspath(__file__))
for fname in sorted(os.listdir(docs_dir)):
    if fname.endswith('.pdf'):
        print(f"\n{'='*80}")
        print(f"FILE: {fname}")
        print(f"{'='*80}")
        fpath = os.path.join(docs_dir, fname)
        text = extract_pdf_text(fpath)
        print(text[:12000])
        print(f"\n... (total chars: {len(text)})")
