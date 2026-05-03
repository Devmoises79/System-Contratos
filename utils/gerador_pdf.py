# utils/gerador_pdf.py
"""
Módulo para geração de PDF de contratos usando ReportLab
Versão simplificada e robusta
"""
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from core.logging_config import logger

# Caminhos
UPLOAD_FOLDER = 'static/uploads/contratos'


def formatar_moeda(valor):
    if valor is None:
        return 'R$ 0,00'
    return f'R$ {valor:,.2f}'.replace(',', 'v').replace('.', ',').replace('v', '.')


def formatar_data(data):
    if not data:
        return 'Nao informada'
    if isinstance(data, str):
        try:
            data = datetime.strptime(data, '%Y-%m-%d')
        except:
            return data
    return data.strftime('%d/%m/%Y')


def formatar_cnpj(cnpj):
    if not cnpj:
        return 'Nao informado'
    cnpj = ''.join(filter(str.isdigit, str(cnpj)))
    if len(cnpj) != 14:
        return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"


def limpar_texto(texto):
    if not texto:
        return ''
    texto = str(texto)
    texto = texto.replace('ç', 'c').replace('Ç', 'C')
    texto = texto.replace('ã', 'a').replace('õ', 'o')
    texto = texto.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    texto = texto.replace('à', 'a').replace('è', 'e').replace('ì', 'i').replace('ò', 'o').replace('ù', 'u')
    texto = texto.replace('â', 'a').replace('ê', 'e').replace('î', 'i').replace('ô', 'o').replace('û', 'u')
    return texto


def gerar_pdf_contrato(contrato):
    """
    Gera PDF do contrato - Versão simplificada
    """
    try:
        # Garantir que a pasta existe
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        pdf_filename = f'contrato_{contrato.numero_contrato}.pdf'
        pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
        
        logger.info(f"Iniciando geracao do PDF: {pdf_path}")
        
        # Criar documento
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            topMargin=2*cm,
            bottomMargin=2*cm,
            leftMargin=2*cm,
            rightMargin=2*cm
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        
        estilo_titulo = ParagraphStyle(
            'Titulo',
            parent=styles['Title'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        estilo_normal = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=5
        )
        
        story = []
        
        # Título
        story.append(Paragraph("CONTRATO DE PRESTACAO DE SERVICOS", estilo_titulo))
        story.append(Spacer(1, 0.5*cm))
        
        # Número do contrato
        story.append(Paragraph(f"<b>Numero do Contrato:</b> {contrato.numero_contrato}", estilo_normal))
        story.append(Spacer(1, 0.3*cm))
        
        # Status
        story.append(Paragraph(f"<b>Status:</b> {contrato.get_status_display()}", estilo_normal))
        story.append(Spacer(1, 0.5*cm))
        
        # Valor
        story.append(Paragraph(f"<b>Valor:</b> {formatar_moeda(contrato.valor)}", estilo_normal))
        story.append(Spacer(1, 0.3*cm))
        
        # Prazo
        story.append(Paragraph(f"<b>Prazo:</b> {contrato.prazo_dias or 'Nao informado'} dias", estilo_normal))
        story.append(Spacer(1, 0.3*cm))
        
        # Datas
        story.append(Paragraph(f"<b>Data de Inicio:</b> {formatar_data(contrato.data_inicio)}", estilo_normal))
        story.append(Paragraph(f"<b>Data de Termino:</b> {formatar_data(contrato.data_fim)}", estilo_normal))
        story.append(Spacer(1, 0.5*cm))
        
        # Contratante
        story.append(Paragraph("<b>CONTRATANTE:</b>", estilo_normal))
        story.append(Paragraph(f"Nome: {limpar_texto(contrato.contratante_nome or '-')}", estilo_normal))
        story.append(Paragraph(f"CNPJ: {formatar_cnpj(contrato.contratante_cnpj)}", estilo_normal))
        story.append(Paragraph(f"Email: {limpar_texto(contrato.contratante_email or '-')}", estilo_normal))
        story.append(Spacer(1, 0.3*cm))
        
        # Contratada
        story.append(Paragraph("<b>CONTRATADA:</b>", estilo_normal))
        story.append(Paragraph(f"Nome: {limpar_texto(contrato.contratada_nome or '-')}", estilo_normal))
        story.append(Paragraph(f"CNPJ: {formatar_cnpj(contrato.contratada_cnpj)}", estilo_normal))
        story.append(Paragraph(f"Email: {limpar_texto(contrato.contratada_email or '-')}", estilo_normal))
        story.append(Spacer(1, 0.5*cm))
        
        # Descrição
        story.append(Paragraph("<b>DESCRICAO:</b>", estilo_normal))
        descricao_texto = limpar_texto(contrato.descricao or 'Nenhuma descricao fornecida.')
        story.append(Paragraph(descricao_texto, estilo_normal))
        story.append(Spacer(1, 0.5*cm))
        
        # Data de geração
        story.append(Paragraph(f"Documento gerado em {datetime.now().strftime('%d/%m/%Y as %H:%M')}", estilo_normal))
        
        # Gerar PDF
        doc.build(story)
        
        logger.info(f"PDF gerado com sucesso: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        import traceback
        traceback.print_exc()
        return None