# Update your utils.py or create a new enhanced PDF generator

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import black, blue, darkblue
import re
from io import BytesIO

def generate_enhanced_pdf(content, title="Summary"):
    """Generate a well-formatted PDF from markdown content"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Create custom styles
    styles = getSampleStyleSheet()
    
    # Custom styles for different elements
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=darkblue,
        alignment=1  # Center alignment
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=blue
    )
    
    subsection_style = ParagraphStyle(
        'SubsectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=15,
        textColor=darkblue
    )
    
    subsubsection_style = ParagraphStyle(
        'SubSubsectionHeader',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=12,
        textColor=black
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        alignment=0,  # Left alignment
        leftIndent=0
    )
    
    bullet_style = ParagraphStyle(
        'BulletPoint',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        leftIndent=20,
        bulletIndent=10
    )
    
    # Story to hold all content
    story = []
    
    # Add title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 20))
    
    # Process content line by line
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
            
        # Section separators
        if line.startswith('---'):
            story.append(PageBreak())
            i += 1
            continue
        
        # Headers
        if line.startswith('# '):
            text = line[2:].strip()
            story.append(Paragraph(text, section_style))
        elif line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(text, subsection_style))
        elif line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, subsubsection_style))
        elif line.startswith('#### '):
            text = line[5:].strip()
            story.append(Paragraph(f"<b>{text}</b>", body_style))
        
        # Bullet points
        elif line.startswith('* ') or line.startswith('- '):
            text = line[2:].strip()
            # Process markdown formatting in bullet points
            text = process_inline_formatting(text)
            story.append(Paragraph(f"• {text}", bullet_style))
        
        # Numbered lists
        elif re.match(r'^\d+\. ', line):
            text = re.sub(r'^\d+\. ', '', line).strip()
            text = process_inline_formatting(text)
            number = re.match(r'^(\d+)\.', line).group(1)
            story.append(Paragraph(f"{number}. {text}", bullet_style))
        
        # Blockquotes
        elif line.startswith('> '):
            text = line[2:].strip()
            text = process_inline_formatting(text)
            quote_style = ParagraphStyle(
                'Quote',
                parent=body_style,
                leftIndent=30,
                rightIndent=30,
                fontName='Helvetica-Oblique',
                textColor=blue
            )
            story.append(Paragraph(f"{text}", quote_style))
        
        # Regular paragraphs
        else:
            if line:
                text = process_inline_formatting(line)
                story.append(Paragraph(text, body_style))
        
        i += 1
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def process_inline_formatting(text):
    """Process markdown inline formatting for PDF"""
    # Bold text
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # Italic text
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    
    # Inline code
    text = re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', text)
    
    # Escape any remaining HTML-like characters
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    # Restore our formatting
    text = text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
    text = text.replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
    text = text.replace('&lt;font name="Courier"&gt;', '<font name="Courier">').replace('&lt;/font&gt;', '</font>')
    
    return text


