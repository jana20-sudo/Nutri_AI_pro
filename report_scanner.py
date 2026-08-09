import pdfplumber
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from pdf2image import convert_from_bytes
import io
import os
import sys

def _setup_tesseract():
    if sys.platform == "win32":
        paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for p in paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                return True
        return False
    return True

def _enhance(img):
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    return img

def extract_text_from_pdf(file_bytes):
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                pt = page.extract_text()
                if pt:
                    text += pt + "\n"
    except Exception as e:
        print(f"[PDF] Error: {e}")
    if len(text.strip()) < 50:
        if not _setup_tesseract():
            return "TESSERACT_NOT_FOUND"
        try:
            images = convert_from_bytes(file_bytes, dpi=300)
            for img in images:
                text += pytesseract.image_to_string(
                    _enhance(img), config="--psm 6 --oem 3"
                ) + "\n"
        except Exception as e:
            print(f"[OCR] Error: {e}")
    return text.strip()

def extract_text_from_image(file_bytes):
    if not _setup_tesseract():
        return "TESSERACT_NOT_FOUND"
    try:
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(
            _enhance(img), config="--psm 6 --oem 3"
        ).strip()
    except Exception as e:
        print(f"[Image OCR] Error: {e}")
        return ""

def extract_report_text(uploaded_file):
    # Fix: Use getvalue() for Streamlit UploadedFile
    try:
        file_bytes = uploaded_file.getvalue()
    except AttributeError:
        uploaded_file.seek(0)
        file_bytes = uploaded_file.read()
    filename = uploaded_file.name.lower()
    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename.endswith((".jpg",".jpeg",".png",".tiff",".webp")):
        return extract_text_from_image(file_bytes)
    return ""