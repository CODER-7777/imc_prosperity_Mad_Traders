import sys
import PyPDF2

def read_pdf(file_path):
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ''
        for page in reader.pages:
            text += page.extract_text() + '\n'
        return text

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python read_pdf.py <pdf_file>")
        sys.exit(1)
    
    try:
        text = read_pdf(sys.argv[1])
        with open("pdf_dump.txt", "w", encoding="utf-8") as out:
            out.write(text)
        print("Successfully dumped to pdf_dump.txt")
    except Exception as e:
        print(f"Error: {e}")
