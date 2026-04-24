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
    text = extract_pdf('D:\\PROSPERITY\\ROUND_2\\Round_2.pdf')
    with open('D:\\PROSPERITY\\ROUND_2\\pdf_summary.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Done")
