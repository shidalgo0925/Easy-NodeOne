#!/usr/bin/env python3
"""
Generador de Reportes Personalizables
Permite crear y exportar reportes en diferentes formatos (CSV, Excel, PDF)
"""

from datetime import datetime
from io import BytesIO, StringIO
import csv
import json

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class ReportGenerator:
    """Generador de reportes en diferentes formatos"""
    
    def __init__(self, data, title="Reporte", columns=None):
        self.data = data
        self.title = title
        self.columns = columns or []
        self.generated_at = datetime.utcnow()
    
    def to_csv(self):
        """Exportar a CSV"""
        output = StringIO()
        
        if isinstance(self.data, list) and len(self.data) > 0:
            # Si es una lista de diccionarios
            if isinstance(self.data[0], dict):
                fieldnames = self.columns if self.columns else list(self.data[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.data)
            else:
                # Si es una lista de listas
                writer = csv.writer(output)
                if self.columns:
                    writer.writerow(self.columns)
                writer.writerows(self.data)
        else:
            # Datos vacíos o formato no reconocido
            writer = csv.writer(output)
            if self.columns:
                writer.writerow(self.columns)
        
        return output.getvalue()
    
    def to_excel(self):
        """Exportar a Excel (xlsx)"""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas y openpyxl son requeridos para exportar a Excel")
        
        # Convertir datos a DataFrame
        if isinstance(self.data, list) and len(self.data) > 0:
            if isinstance(self.data[0], dict):
                df = pd.DataFrame(self.data)
            else:
                df = pd.DataFrame(self.data, columns=self.columns)
        else:
            df = pd.DataFrame(columns=self.columns)
        
        # Crear archivo en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Reporte', index=False)
        
        output.seek(0)
        return output.getvalue()
    
    def to_pdf(self):
        """Exportar a PDF"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab es requerido para exportar a PDF")
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#6f42c1'),
            spaceAfter=30
        )
        
        # Título
        elements.append(Paragraph(self.title, title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Información del reporte
        info_text = f"Generado el: {self.generated_at.strftime('%d/%m/%Y %H:%M:%S')}"
        elements.append(Paragraph(info_text, styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Tabla de datos
        if isinstance(self.data, list) and len(self.data) > 0:
            # Preparar datos para la tabla
            if isinstance(self.data[0], dict):
                headers = self.columns if self.columns else list(self.data[0].keys())
                table_data = [headers]
                for row in self.data:
                    table_data.append([str(row.get(col, '')) for col in headers])
            else:
                table_data = [self.columns] if self.columns else []
                table_data.extend(self.data)
            
            # Crear tabla
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6f42c1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("No hay datos para mostrar", styles['Normal']))
        
        # Construir PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    def to_json(self):
        """Exportar a JSON"""
        return json.dumps({
            'title': self.title,
            'generated_at': self.generated_at.isoformat(),
            'columns': self.columns,
            'data': self.data
        }, indent=2, ensure_ascii=False)


def generate_custom_report(data, format_type='csv', title="Reporte", columns=None):
    """Función helper para generar reportes"""
    generator = ReportGenerator(data, title, columns)
    
    if format_type.lower() == 'csv':
        return generator.to_csv(), 'text/csv', f'{title.replace(" ", "_")}.csv'
    elif format_type.lower() == 'excel' or format_type.lower() == 'xlsx':
        return generator.to_excel(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', f'{title.replace(" ", "_")}.xlsx'
    elif format_type.lower() == 'pdf':
        return generator.to_pdf(), 'application/pdf', f'{title.replace(" ", "_")}.pdf'
    elif format_type.lower() == 'json':
        return generator.to_json(), 'application/json', f'{title.replace(" ", "_")}.json'
    else:
        raise ValueError(f"Formato no soportado: {format_type}")

