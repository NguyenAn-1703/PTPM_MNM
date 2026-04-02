import pytesseract
print('tesseract_cmd=', pytesseract.pytesseract.tesseract_cmd)
try:
    print('version=', pytesseract.get_tesseract_version())
    print('langs=', pytesseract.get_languages(config=''))
except Exception as e:
    print('err=', repr(e))