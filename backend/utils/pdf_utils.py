import io
from reportlab.lib.pagesizes import letter, A4 # Keeping letter as it was in your provided code
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import black, blue, darkblue, Color # Import Color for custom shades
from reportlab.lib import units # Changed: Import units module directly
import re

# Define a slightly lighter blue for main headings for better contrast
light_blue = Color(0.1, 0.4, 0.7) # R, G, B values from 0.0 to 1.0

def generate_enhanced_pdf(content: str, title: str = "Document Summary") -> io.BytesIO:
    """
    Generates a PDF from a given content string, adding a title and basic formatting.
    The content can include basic markdown for headings, lists, and inline formatting.

    Args:
        content: The text content to convert to PDF. Supports basic markdown.
        title: The title for the PDF document.

    Returns:
        A BytesIO object containing the PDF data.
    """
    buffer = io.BytesIO()
    # Using 'letter' as per your provided code, not A4 from previous suggestion
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=units.inch/2, leftMargin=units.inch/2, # Changed: units.inch
                            topMargin=units.inch/2, bottomMargin=units.inch/2) # Changed: units.inch
    
    # Create custom styles
    styles = getSampleStyleSheet()
    
    # Custom styles for different elements
    # Main Document Title (e.g., "Summary: Web: https://amazon.in")
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['h1'],
        fontSize=20, # Reduced from 24 to 20
        leading=24,
        textColor=darkblue, # Using darkblue for a more appealing, less harsh look
        alignment=TA_CENTER,  # Center alignment
        spaceAfter=0.2*units.inch # Changed: units.inch
    )
    
    # Markdown Level 1 Header (# Section)
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['h2'], # Based on default h2, but customized
        fontSize=16, # Slightly larger for main sections
        leading=18,
        spaceAfter=12,
        spaceBefore=20,
        textColor=light_blue # A distinct blue for sections
    )
    
    # Markdown Level 2 Header (## Subsection)
    subsection_style = ParagraphStyle(
        'SubsectionHeader',
        parent=styles['h3'], # Based on default h3, but customized
        fontSize=14,
        leading=16,
        spaceAfter=10,
        spaceBefore=15,
        textColor=blue # Original blue for sub-sections
    )
    
    # Markdown Level 3 Header (### SubSubsection)
    subsubsection_style = ParagraphStyle(
        'SubSubsectionHeader',
        parent=styles['h4'], # Based on default h4, but customized
        fontSize=12,
        leading=14,
        spaceAfter=8,
        spaceBefore=12,
        textColor=black # Black for lowest level headings
    )

    # Style for inferred plain-text headings (like "Overview", "Key Product Categories & Deals")
    plain_heading_style = ParagraphStyle(
        'PlainHeadingStyle',
        parent=styles['h2'], # Similar to a subsection header
        fontSize=14,
        leading=16,
        spaceAfter=10,
        spaceBefore=15,
        textColor=darkblue,
        fontName='Helvetica-Bold' # Make it bold
    )
    
    # Body text style
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        spaceAfter=6,
        alignment=TA_LEFT,  # Left alignment
        leftIndent=0
    )
    
    # Bullet point style
    bullet_style = ParagraphStyle(
        'BulletPoint',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        spaceAfter=4,
        leftIndent=20,
        bulletIndent=10 # Indent bullet character
    )

    # Blockquote style
    quote_style = ParagraphStyle(
        'Quote',
        parent=body_style,
        leftIndent=30,
        rightIndent=30,
        fontName='Helvetica-Oblique',
        textColor=blue,
        backColor=Color(0.95, 0.95, 1, 0.5), # Light blue background for quotes
        borderPadding=5,
        borderColor=blue,
        borderWidth=0.5,
        borderRadius=5,
        spaceBefore=10,
        spaceAfter=10
    )
    
    # Story to hold all content
    story = []
    
    # Add title (e.g., "Summary: Web: https://amazon.in")
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.2 * units.inch)) # Changed: units.inch # Add a spacer after the title for consistent spacing
    
    # Process content line by line
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            story.append(Spacer(1, 0.1 * units.inch)) # Changed: units.inch # Add small space for empty line
            i += 1
            continue
            
        # Specific handling for "--- PAGE X ---" artifacts - skip these lines
        if re.match(r'^---\s*PAGE\s*\d+\s*---$', line, re.IGNORECASE):
            # This line indicates a page break in the source text, don't print it.
            # A PageBreak() for the actual --- separator is handled below if needed.
            i += 1
            continue
        
        # Section separators (general '---' to indicate a hard page break)
        if line == '---':
            story.append(PageBreak())
            i += 1
            continue
        
        # Markdown Headers
        if line.startswith('# '):
            text = line[2:].strip()
            story.append(Paragraph(process_inline_formatting(text), section_style))
        elif line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(process_inline_formatting(text), subsection_style))
        elif line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(process_inline_formatting(text), subsubsection_style))
        elif line.startswith('#### '): # Treat H4 as bolded body text
            text = line[5:].strip()
            story.append(Paragraph(f"<b>{process_inline_formatting(text)}</b>", body_style))
        
        # Bullet points
        elif line.startswith('* ') or line.startswith('- '):
            text = line[2:].strip()
            text = process_inline_formatting(text)
            story.append(Paragraph(f"• {text}", bullet_style))
        
        # Numbered lists
        elif re.match(r'^\d+\.\s', line): # Matches "1. ", "2. ", etc.
            text = re.sub(r'^\d+\.\s*', '', line).strip() # Remove the number and dot
            text = process_inline_formatting(text)
            number = re.match(r'^(\d+)\.', line).group(1) # Extract the number
            story.append(Paragraph(f"{number}. {text}", bullet_style))
        
        # Blockquotes
        elif line.startswith('> '):
            text = line[2:].strip()
            text = process_inline_formatting(text)
            story.append(Paragraph(f"{text}", quote_style))
        
        # Heuristic for plain-text headings (like "Overview", "Key Product Categories & Deals")
        # This checks if a line is likely a heading by checking its length, capitalization,
        # and if it's followed by what appears to be body text (not another heading/list).
        elif len(line.split()) < 10 and (line.isupper() or (line[0].isupper() and (line.endswith(':') or all(word.istitle() or word.isupper() for word in line.split())))):
            next_is_body = False
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                if next_line:
                    # If the next non-empty line does NOT start with common markdown markers, it's likely body text.
                    if not (next_line.startswith(('#', '*', '-', '>')) or re.match(r'^\d+\.\s', next_line)):
                        next_is_body = True
                    break # Found next non-empty line, stop checking
            
            if next_is_body:
                story.append(Paragraph(process_inline_formatting(line), plain_heading_style))
            else: # If not followed by body text (e.g., followed by another heading/list), treat as regular paragraph
                story.append(Paragraph(process_inline_formatting(line), body_style))
                
        # Regular paragraphs
        else:
            if line:
                story.append(Paragraph(process_inline_formatting(line), body_style))
        
        i += 1
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def process_inline_formatting(text):
    """
    Process markdown inline formatting (bold, italic, inline code) for ReportLab's rich text.
    Handles HTML escaping carefully to avoid ReportLab misinterpretation.
    """
    # Replace allowed tags with unique placeholders first
    text = text.replace('<b>', '&&_B_&&').replace('</b>', '&&_/B_&&')
    text = text.replace('<i>', '&&_I_&&').replace('</i>', '&&_/I_&&')
    text = text.replace('<font name="Courier">', '&&_FC_&&').replace('</font>', '&&_/FC_&&')

    # Escape all other HTML characters
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Restore our formatting placeholders back to actual ReportLab-compatible tags
    text = text.replace('&&_B_&&', '<b>').replace('&&_/B_&&', '</b>')
    text = text.replace('&&_I_&&', '<i>').replace('&&_/I_&&', '</i>')
    text = text.replace('&&_FC_&&', '<font name="Courier">').replace('&&_/FC_&&', '</font>')

    # Bold text: **text** -> <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # Italic text: *text* -> <i>text</i> (this regex is simple and might catch things if not careful,
    # but works for typical usage outside of **bold** context)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    
    # Inline code: `code` -> <font name="Courier">code</font>
    text = re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', text)
    
    return text
