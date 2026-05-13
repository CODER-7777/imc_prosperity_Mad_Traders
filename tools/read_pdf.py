import PyPDF2
import sys

def extract_pdf(pdf_path):
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        text = []
        for page in reader.pages:
            text.append(page.extract_text())
        return "\n".join(text)
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python read_pdf.py <path_to_pdf>")
        sys.exit(1)
    text = extract_pdf(sys.argv[1])
    print(text)
