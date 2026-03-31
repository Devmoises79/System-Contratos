# utils/gerador_pdf.py
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

def gerar_pdf_contrato(contrato):
    """Gera o PDF do contrato"""
    
    # Cria diretório se não existir
    pdf_dir = 'static/uploads/contratos'
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Nome do arquivo
    filename = f'contrato_{contrato.numero_contrato}.pdf'
    filepath = os.path.join(pdf_dir, filename)
    
    # Cria o documento
    doc = SimpleDocTemplate(filepath, pagesize=A4, 
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    
    # Estilos
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    subtitulo_style = ParagraphStyle(
        'Subtitulo',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=12
    )
    
    # Conteúdo do PDF
    story = []
    
    # Título
    story.append(Paragraph("CONTRATO DE PRESTAÇÃO DE SERVIÇOS", titulo_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Número do contrato
    story.append(Paragraph(f"Nº {contrato.numero_contrato}", subtitulo_style))
    story.append(Spacer(1, 1*cm))
    
    # Data
    data_atual = datetime.now().strftime("%d/%m/%Y")
    story.append(Paragraph(f"Data: {data_atual}", normal_style))
    story.append(Spacer(1, 1*cm))
    
    # Partes
    story.append(Paragraph("<b>CONTRATANTE:</b>", normal_style))
    story.append(Paragraph(f"{contrato.contratante_nome}", normal_style))
    if contrato.contratante_cnpj:
        story.append(Paragraph(f"CNPJ/CPF: {contrato.contratante_cnpj}", normal_style))
    if contrato.contratante_email:
        story.append(Paragraph(f"Email: {contrato.contratante_email}", normal_style))
    if contrato.contratante_telefone:
        story.append(Paragraph(f"Telefone: {contrato.contratante_telefone}", normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("<b>CONTRATADA:</b>", normal_style))
    story.append(Paragraph(f"{contrato.contratada_nome}", normal_style))
    if contrato.contratada_cnpj:
        story.append(Paragraph(f"CNPJ/CPF: {contrato.contratada_cnpj}", normal_style))
    if contrato.contratada_email:
        story.append(Paragraph(f"Email: {contrato.contratada_email}", normal_style))
    story.append(Spacer(1, 1*cm))
    
    # Cláusulas
    story.append(Paragraph("<b>CLÁUSULA PRIMEIRA - DO OBJETO</b>", normal_style))
    story.append(Paragraph(
        "O presente contrato tem como objeto a prestação de serviços conforme descrição abaixo:",
        normal_style
    ))
    story.append(Paragraph(contrato.descricao or "Não especificado", normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("<b>CLÁUSULA SEGUNDA - DO VALOR</b>", normal_style))
    story.append(Paragraph(
        f"Pela execução dos serviços, a CONTRATANTE pagará à CONTRATADA o valor de R$ {contrato.valor:,.2f}.",
        normal_style
    ))
    story.append(Spacer(1, 0.5*cm))
    
    story.append(Paragraph("<b>CLÁUSULA TERCEIRA - DO PRAZO</b>", normal_style))
    story.append(Paragraph(
        f"O prazo para execução dos serviços é de {contrato.prazo_dias} dias, contados a partir da assinatura do presente contrato.",
        normal_style
    ))
    story.append(Spacer(1, 1*cm))
    
    # Assinaturas
    story.append(Paragraph("<b>ASSINATURAS</b>", normal_style))
    story.append(Spacer(1, 1*cm))
    
    # Tabela de assinaturas
    data = [
        ["_________________________", "_________________________"],
        [contrato.contratante_nome, contrato.contratada_nome],
        ["Contratante", "Contratada"]
    ]
    
    table = Table(data, colWidths=[7*cm, 7*cm])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
    ]))
    
    story.append(table)
    
    # Gera o PDF
    doc.build(story)
    
    return filepath