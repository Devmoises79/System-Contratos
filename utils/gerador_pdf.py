"""
Gerador de PDF para contratos - Versão Simplificada e Garantida
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from core.logging_config import logger

def gerar_pdf_contrato(contrato):
    """
    Gera o PDF do contrato usando ReportLab
    Retorna o caminho do arquivo gerado ou None em caso de erro
    """
    # Cria diretório se não existir
    pdf_dir = os.path.abspath('static/uploads/contratos')
    os.makedirs(pdf_dir, exist_ok=True)
    
    # Nome do arquivo
    pdf_filename = f'contrato_{contrato.numero_contrato}.pdf'
    pdf_path = os.path.join(pdf_dir, pdf_filename)
    
    logger.info(f"Iniciando geração do PDF: {pdf_path}")
    
    try:
        # Cria o documento
        doc = SimpleDocTemplate(pdf_path, pagesize=A4,
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
        
        negrito_style = ParagraphStyle(
            'Negrito',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=6,
            fontName='Helvetica-Bold'
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
        data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")
        story.append(Paragraph(f"Data de emissão: {data_atual}", normal_style))
        story.append(Spacer(1, 1*cm))
        
        # PARTES
        story.append(Paragraph("<b>PARTES CONTRATANTES</b>", negrito_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Contratante
        story.append(Paragraph("<b>CONTRATANTE:</b>", negrito_style))
        contratante_nome = contrato.contratante_nome or 'Não informado'
        story.append(Paragraph(f"Empresa: {contratante_nome}", normal_style))
        if contrato.contratante_cnpj:
            story.append(Paragraph(f"CNPJ/CPF: {contrato.contratante_cnpj}", normal_style))
        if contrato.contratante_email:
            story.append(Paragraph(f"E-mail: {contrato.contratante_email}", normal_style))
        if contrato.contratante_telefone:
            story.append(Paragraph(f"Telefone: {contrato.contratante_telefone}", normal_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Contratada
        story.append(Paragraph("<b>CONTRATADA:</b>", negrito_style))
        contratada_nome = contrato.contratada_nome or 'Não informado'
        story.append(Paragraph(f"Empresa: {contratada_nome}", normal_style))
        if contrato.contratada_cnpj:
            story.append(Paragraph(f"CNPJ/CPF: {contrato.contratada_cnpj}", normal_style))
        if contrato.contratada_email:
            story.append(Paragraph(f"E-mail: {contrato.contratada_email}", normal_style))
        story.append(Spacer(1, 1*cm))
        
        # CLÁUSULAS
        story.append(Paragraph("<b>CLÁUSULAS CONTRATUAIS</b>", negrito_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Cláusula 1 - Objeto
        story.append(Paragraph("<b>CLÁUSULA PRIMEIRA - DO OBJETO</b>", negrito_style))
        story.append(Paragraph(
            "O presente contrato tem como objeto a prestação de serviços conforme descrição abaixo:",
            normal_style
        ))
        descricao = contrato.descricao or "Não especificado"
        story.append(Paragraph(descricao, normal_style))
        story.append(Spacer(1, 0.5*cm))
        
        # Cláusula 2 - Valor
        story.append(Paragraph("<b>CLÁUSULA SEGUNDA - DO VALOR</b>", negrito_style))
        valor_str = f"R$ {contrato.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        story.append(Paragraph(
            f"Pela execução dos serviços, a CONTRATANTE pagará à CONTRATADA o valor de <b>{valor_str}</b>.",
            normal_style
        ))
        story.append(Spacer(1, 0.5*cm))
        
        # Cláusula 3 - Prazo
        if contrato.prazo_dias:
            story.append(Paragraph("<b>CLÁUSULA TERCEIRA - DO PRAZO</b>", negrito_style))
            story.append(Paragraph(
                f"O prazo para execução dos serviços é de <b>{contrato.prazo_dias} dias</b>, contados a partir da assinatura do presente contrato.",
                normal_style
            ))
            story.append(Spacer(1, 0.5*cm))
        
        # Cláusula 4 - Vigência
        if contrato.data_inicio or contrato.data_fim:
            story.append(Paragraph("<b>CLÁUSULA QUARTA - DA VIGÊNCIA</b>", negrito_style))
            vigencia = ""
            if contrato.data_inicio:
                data_ini = contrato.data_inicio if isinstance(contrato.data_inicio, str) else contrato.data_inicio.strftime('%d/%m/%Y')
                vigencia += f"a partir de <b>{data_ini}</b>"
            if contrato.data_fim:
                data_fim = contrato.data_fim if isinstance(contrato.data_fim, str) else contrato.data_fim.strftime('%d/%m/%Y')
                vigencia += f" até <b>{data_fim}</b>"
            story.append(Paragraph(f"O presente contrato terá vigência {vigencia}.", normal_style))
            story.append(Spacer(1, 0.5*cm))
        
        # ASSINATURAS
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("<b>ASSINATURAS</b>", negrito_style))
        story.append(Spacer(1, 1*cm))
        
        # Tabela de assinaturas
        data_table = [
            ["_________________________", "_________________________"],
            [contratante_nome, contratada_nome],
            ["Contratante", "Contratada"],
            ["", ""],
            [data_atual.split(' às')[0], data_atual.split(' às')[0]]
        ]
        
        table = Table(data_table, colWidths=[7*cm, 7*cm])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        story.append(table)
        
        # Rodapé
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(
            "<i>Documento gerado eletronicamente por ValidaPy - Sistema de Gestão de Contratos</i>",
            ParagraphStyle('Rodape', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)
        ))
        
        # Gera o PDF
        doc.build(story)
        
        logger.info(f" PDF gerado com sucesso: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f" Erro ao gerar PDF: {str(e)}")
        return None