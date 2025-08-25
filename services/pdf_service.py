import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_payroll_pdf(html_content: str, filename: str) -> str:
    """
    Generate PDF from HTML content using WeasyPrint or ReportLab fallback.
    Returns path to generated PDF file.
    
    Args:
        html_content (str): HTML content with CSS styling
        filename (str): Desired filename for the PDF
        
    Returns:
        str: Path to generated PDF file
    
    Raises:
        ImportError: If neither WeasyPrint nor ReportLab is available
    """
    # Create temp directory for PDF
    temp_dir = tempfile.mkdtemp()
    temp_pdf_path = os.path.join(temp_dir, filename)

    try:
        # Try WeasyPrint first with error handling
        try:
            from weasyprint import HTML, CSS
            
            # Clean up problematic CSS properties that cause warnings/errors
            cleaned_html = clean_html_for_weasyprint(html_content)
            
            logger.info("Attempting to generate PDF with WeasyPrint...")
            HTML(string=cleaned_html).write_pdf(temp_pdf_path)
            logger.info(f"PDF generated successfully with WeasyPrint: {temp_pdf_path}")
            return temp_pdf_path
            
        except ImportError as e:
            logger.warning(f"WeasyPrint not available: {e}")
            raise ImportError("WeasyPrint not available")
        except Exception as e:
            logger.error(f"WeasyPrint failed: {e}")
            # Continue to ReportLab fallback
            
        # Fallback to ReportLab
        try:
            logger.info("Falling back to ReportLab...")
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            
            # Create PDF with ReportLab
            doc = SimpleDocTemplate(temp_pdf_path, pagesize=A4, 
                                  leftMargin=0.5*inch, rightMargin=0.5*inch,
                                  topMargin=0.5*inch, bottomMargin=0.5*inch)
            styles = getSampleStyleSheet()
            
            # Create custom styles for payslip
            payslip_style = ParagraphStyle(
                'PayslipStyle',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                alignment=1  # Center alignment
            )
            
            header_style = ParagraphStyle(
                'HeaderStyle',
                parent=styles['Heading1'],
                fontSize=14,
                alignment=1,
                spaceAfter=12
            )
            
            # Convert HTML to ReportLab story
            story = generate_reportlab_story(html_content, styles, payslip_style, header_style)
            
            # Build PDF
            doc.build(story)
            logger.info(f"PDF generated successfully with ReportLab: {temp_pdf_path}")
            return temp_pdf_path
            
        except ImportError as e:
            logger.error(f"ReportLab not available: {e}")
            raise ImportError(
                "Neither WeasyPrint nor ReportLab is available. "
                "Please install one of them: \n"
                "pip install weasyprint\n"
                "- or -\n"
                "pip install reportlab"
            )
        except Exception as e:
            logger.error(f"ReportLab failed: {e}")
            raise e
                
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except:
                pass
        logger.error(f"PDF generation failed: {e}")
        raise e

def clean_html_for_weasyprint(html_content: str) -> str:
    """
    Clean HTML content to remove problematic CSS properties for WeasyPrint
    """
    # Remove problematic CSS properties that cause warnings
    problematic_properties = [
        'gap: 2%',
        'print-color-adjust: exact',
        '-webkit-print-color-adjust: exact'
    ]
    
    cleaned_html = html_content
    for prop in problematic_properties:
        cleaned_html = cleaned_html.replace(prop, '')
    
    # Replace gap with margin for better compatibility
    cleaned_html = cleaned_html.replace('gap: 2%;', 'margin: 0 1%;')
    
    return cleaned_html

def generate_reportlab_story(html_content: str, styles, payslip_style, header_style):
    """
    Convert HTML content to ReportLab story for PDF generation
    """
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    
    story = []
    
    # Extract text content from HTML (simplified parsing)
    lines = html_content.split('\n')
    current_section = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Handle headers
        if '<h2>' in line and 'SSPL CONSTRUCTIONS' in line:
            story.append(Paragraph("SSPL CONSTRUCTIONS PVT LTD", header_style))
            story.append(Spacer(1, 12))
        elif '<h4>' in line and 'EARNINGS' in line:
            story.append(Paragraph("EARNINGS", payslip_style))
            story.append(Spacer(1, 6))
        elif '<h4>' in line and 'DEDUCTIONS' in line:
            story.append(Paragraph("DEDUCTIONS", payslip_style))
            story.append(Spacer(1, 6))
        elif '<strong>NET SALARY:' in line:
            # Extract net salary amount
            import re
            salary_match = re.search(r'₹([\d,]+\.?\d*)', line)
            if salary_match:
                net_salary = salary_match.group(1)
                story.append(Paragraph(f"NET SALARY: ₹{net_salary}", header_style))
                story.append(Spacer(1, 12))
        elif '<td>' in line and '</td>' in line:
            # Handle table rows
            cells = line.split('<td>')
            if len(cells) >= 3:
                cell1 = cells[1].replace('</td>', '').strip()
                cell2 = cells[2].replace('</td>', '').strip()
                if cell1 and cell2:
                    story.append(Paragraph(f"{cell1}: {cell2}", payslip_style))
    
    return story

# Example usage
if __name__ == "__main__":
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            .header { text-align: center; color: navy; }
            .payslip { 
                border: 1px solid black;
                padding: 20px;
                margin: 20px;
            }
            table { width: 100%; border-collapse: collapse; }
            td { padding: 5px; border: 1px solid #ccc; }
        </style>
    </head>
    <body>
        <div class="payslip">
            <h1 class="header">Sample Payslip</h1>
            <table>
                <tr>
                    <td>Employee Name:</td>
                    <td>John Doe</td>
                </tr>
                <tr>
                    <td>Basic Salary:</td>
                    <td>$5000</td>
                </tr>
            </table>
        </div>
    </body>
    </html>
    """
    
    try:
        pdf_path = generate_payroll_pdf(sample_html, "sample_payslip.pdf")
        print(f"PDF generated successfully at: {pdf_path}")
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")