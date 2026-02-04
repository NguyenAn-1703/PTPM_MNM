"""
Document Processor Module
Xử lý các loại tài liệu: PDF, Word, Image (OCR)
"""
import os
from typing import Optional
from pypdf import PdfReader
from docx import Document
from PIL import Image
import pytesseract


def extract_text_from_pdf(file_path: str) -> str:
    """
    Trích xuất text từ file PDF sử dụng PyPDF
    """
    try:
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except Exception as e:
        raise Exception(f"Lỗi khi đọc PDF: {str(e)}")


def extract_text_from_docx(file_path: str) -> str:
    """
    Trích xuất text từ file Word (.docx) sử dụng python-docx
    """
    try:
        doc = Document(file_path)
        text_parts = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        # Cũng trích xuất text từ tables
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text_parts.append(" | ".join(row_text))
        
        return "\n\n".join(text_parts)
    except Exception as e:
        raise Exception(f"Lỗi khi đọc Word: {str(e)}")


def extract_text_from_image(file_path: str, lang: str = 'vie+eng') -> str:
    """
    Trích xuất text từ ảnh sử dụng Tesseract OCR
    Hỗ trợ tiếng Việt và tiếng Anh
    
    Args:
        file_path: Đường dẫn đến file ảnh
        lang: Ngôn ngữ OCR (mặc định: vie+eng cho tiếng Việt + Anh)
    """
    try:
        image = Image.open(file_path)
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        text = pytesseract.image_to_string(image, lang=lang)
        return text.strip()
    except Exception as e:
        raise Exception(f"Lỗi khi OCR ảnh: {str(e)}")


def process_document(file_path: str, file_type: str) -> str:
    """
    Xử lý tài liệu dựa trên loại file
    
    Args:
        file_path: Đường dẫn đến file
        file_type: Loại file (pdf, docx, png, jpg, jpeg)
    
    Returns:
        Text đã trích xuất từ tài liệu
    """
    file_type = file_type.lower()
    
    if file_type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_type in ['docx', 'doc']:
        return extract_text_from_docx(file_path)
    elif file_type in ['png', 'jpg', 'jpeg', 'bmp', 'tiff']:
        return extract_text_from_image(file_path)
    else:
        raise ValueError(f"Không hỗ trợ định dạng file: {file_type}")


def get_file_extension(filename: str) -> str:
    """Lấy extension của file"""
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
