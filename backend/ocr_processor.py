#!/usr/bin/env python3
"""
Módulo para procesamiento OCR de comprobantes de pago usando EasyOCR
"""

import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("⚠️ EasyOCR no está instalado. Instala con: pip install easyocr")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ Pillow no está instalado. Instala con: pip install Pillow")

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("⚠️ pdf2image no está instalado. Instala con: pip install pdf2image")


class OCRProcessor:
    """Procesador OCR para extraer información de comprobantes de pago"""
    
    def __init__(self, languages=['en', 'es']):
        """Inicializar EasyOCR reader"""
        self.languages = languages
        self.reader = None
        
        if EASYOCR_AVAILABLE:
            try:
                print("🔄 Inicializando EasyOCR...")
                self.reader = easyocr.Reader(languages, gpu=False)
                print("✅ EasyOCR inicializado correctamente")
            except Exception as e:
                print(f"⚠️ Error inicializando EasyOCR: {e}")
                self.reader = None
        else:
            print("⚠️ EasyOCR no disponible")
    
    def extract_text_from_image(self, image_path):
        """Extraer texto de una imagen"""
        if not self.reader:
            return None, "EasyOCR no está disponible"
        
        try:
            results = self.reader.readtext(image_path)
            # Combinar todo el texto extraído
            full_text = ' '.join([result[1] for result in results])
            return full_text, None
        except Exception as e:
            return None, str(e)
    
    def extract_text_from_pdf(self, pdf_path):
        """Extraer texto de un PDF convirtiéndolo a imágenes"""
        if not PDF2IMAGE_AVAILABLE:
            return None, "pdf2image no está disponible"
        
        if not self.reader:
            return None, "EasyOCR no está disponible"
        
        try:
            # Convertir PDF a imágenes
            images = convert_from_path(pdf_path, dpi=300)
            all_text = []
            
            for img in images:
                # Guardar imagen temporal
                temp_path = pdf_path.replace('.pdf', '_temp.png')
                img.save(temp_path, 'PNG')
                
                # Extraer texto
                text, error = self.extract_text_from_image(temp_path)
                if text:
                    all_text.append(text)
                
                # Eliminar temporal
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
            return ' '.join(all_text), None
        except Exception as e:
            return None, str(e)
    
    def extract_payment_data(self, file_path):
        """
        Extraer datos de pago del documento
        
        Retorna:
            dict con: amount, date, reference, bank, account_number, payer_name
            o None si hay error
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Extraer texto según el tipo de archivo
        if file_ext == '.pdf':
            text, error = self.extract_text_from_pdf(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            text, error = self.extract_text_from_image(file_path)
        else:
            return None, f"Formato de archivo no soportado: {file_ext}"
        
        if error:
            return None, error
        
        if not text:
            return None, "No se pudo extraer texto del documento"
        
        # Procesar texto para extraer información
        extracted_data = {
            'amount': self._extract_amount(text),
            'date': self._extract_date(text),
            'reference': self._extract_reference(text),
            'bank': self._extract_bank(text),
            'account_number': self._extract_account_number(text),
            'payer_name': self._extract_payer_name(text),
            'raw_text': text[:500]  # Primeros 500 caracteres para referencia
        }
        
        return extracted_data, None
    
    def _extract_amount(self, text):
        """Extraer monto del texto"""
        # Patrones comunes para montos
        patterns = [
            r'\$\s*(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d{2})?)',  # $60.00, $1,234.56
            r'(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d{2})?)\s*USD',  # 60.00 USD
            r'monto[:\s]+(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d{2})?)',  # monto: 60.00
            r'amount[:\s]+(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d{2})?)',  # amount: 60.00
            r'total[:\s]+(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d{2})?)',  # total: 60.00
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # Limpiar formato (remover comas, convertir punto decimal)
                    amount_str = matches[-1].replace(',', '').replace('.', '')
                    # Si tiene más de 2 dígitos después del punto, asumir que el punto es decimal
                    if '.' in matches[-1] or len(amount_str) > 2:
                        amount_str = matches[-1].replace(',', '')
                        if ',' in amount_str:
                            amount_str = amount_str.replace('.', '').replace(',', '.')
                    else:
                        amount_str = matches[-1].replace(',', '').replace('.', '')
                        amount_str = amount_str[:-2] + '.' + amount_str[-2:]
                    
                    amount = float(amount_str)
                    return round(amount, 2)
                except:
                    continue
        
        return None
    
    def _extract_date(self, text):
        """Extraer fecha del texto"""
        # Patrones comunes para fechas
        patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # DD/MM/YYYY o DD-MM-YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD
            r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',  # DD de Mes de YYYY (español)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    match = matches[0]
                    if len(match) == 3:
                        if len(match[2]) == 4:  # YYYY
                            if int(match[0]) > 12:  # DD/MM/YYYY
                                day, month, year = match
                            else:  # MM/DD/YYYY o YYYY/MM/DD
                                if int(match[0]) > 31:
                                    year, month, day = match
                                else:
                                    month, day, year = match
                        else:  # DD/MM/YY
                            day, month, year = match
                            year = '20' + year if int(year) < 50 else '19' + year
                        
                        return f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                except:
                    continue
        
        return None
    
    def _extract_reference(self, text):
        """Extraer número de referencia o transacción"""
        patterns = [
            r'referencia[:\s]+([A-Z0-9-]+)',  # referencia: BG-12345678
            r'reference[:\s]+([A-Z0-9-]+)',  # reference: BG-12345678
            r'transacci[oó]n[:\s]+([A-Z0-9-]+)',  # transacción: BG-12345678
            r'([A-Z]{2,3}[-]\d{6,12})',  # BG-12345678, YAPPY-12345678
            r'(\d{10,20})',  # Números largos (posible referencia)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].upper()
        
        return None
    
    def _extract_bank(self, text):
        """Extraer nombre del banco"""
        banks = [
            'banco general', 'banco general panama', 'banco general panamá',
            'banco nacional', 'banco nacional de panama',
            'banistmo', 'banco banistmo',
            'bac', 'bac panama',
            'yappy', 'yappy panama',
            'interbank', 'banco interbank',
            'paypal', 'pay pal'
        ]
        
        text_lower = text.lower()
        for bank in banks:
            if bank in text_lower:
                return bank.title()
        
        return None
    
    def _extract_account_number(self, text):
        """Extraer número de cuenta"""
        patterns = [
            r'cuenta[:\s]+([\d-]+)',  # cuenta: 03-78-01-089981-8
            r'account[:\s]+([\d-]+)',  # account: 03-78-01-089981-8
            r'cci[:\s]+([\d-]+)',  # CCI: 003-898-013466252745-43
            r'(\d{2,3}[-]\d{2}[-]\d{2}[-]\d{6,12}[-]\d{1,2})',  # Formato cuenta bancaria
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None
    
    def _extract_payer_name(self, text):
        """Extraer nombre del pagador"""
        patterns = [
            r'de[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # De: Juan Pérez
            r'pagador[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # pagador: Juan Pérez
            r'payer[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # payer: Juan Pérez
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        return None


# Instancia global del procesador OCR
_ocr_processor = None

def get_ocr_processor():
    """Obtener instancia global del procesador OCR"""
    global _ocr_processor
    if _ocr_processor is None and EASYOCR_AVAILABLE:
        _ocr_processor = OCRProcessor()
    return _ocr_processor

