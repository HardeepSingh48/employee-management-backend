import os
import tempfile
import logging
from pathlib import Path
from typing import Optional
import platform

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_payroll_pdf(html_content: str, filename: str) -> str:
    """
    Generate PDF from HTML content with enhanced server compatibility.
    Returns path to generated PDF file.
    
    Args:
        html_content (str): HTML content with CSS styling
        filename (str): Desired filename for the PDF
        
    Returns:
        str: Path to generated PDF file
    
    Raises:
        ImportError: If no PDF generation library is available
    """
    # Create temp directory for PDF
    temp_dir = tempfile.mkdtemp()
    temp_pdf_path = os.path.join(temp_dir, filename)

    try:
        # Try WeasyPrint first with server-specific configurations
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            logger.info("Attempting to generate PDF with WeasyPrint...")
            
            # Clean up HTML for better server compatibility
            cleaned_html = clean_html_for_server(html_content)
            
            # Create font configuration for server environments
            font_config = FontConfiguration()
            
            # Server-specific WeasyPrint options
            html_doc = HTML(string=cleaned_html, base_url="")
            
            # Generate PDF with specific options for server environments
            html_doc.write_pdf(
                temp_pdf_path,
                font_config=font_config,
                optimize_images=True,
                pdf_version="1.4"  # Better compatibility
            )
            
            logger.info(f"PDF generated successfully with WeasyPrint: {temp_pdf_path}")
            return temp_pdf_path
            
        except ImportError as e:
            logger.warning(f"WeasyPrint not available: {e}")
            raise ImportError("WeasyPrint not available")
        except Exception as e:
            logger.error(f"WeasyPrint failed: {e}")
            # Continue to ReportLab fallback
            
        # Enhanced ReportLab fallback with better layout control
        try:
            logger.info("Falling back to ReportLab...")
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch, mm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import re
            from bs4 import BeautifulSoup
            
            # Register default fonts if available
            try:
                # Try to register system fonts
                pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
            except:
                # Use built-in fonts as fallback
                pass
            
            # Create PDF with ReportLab using exact dimensions
            doc = SimpleDocTemplate(
                temp_pdf_path, 
                pagesize=A4,
                leftMargin=8*mm,    # 0.3cm
                rightMargin=8*mm,   # 0.3cm
                topMargin=8*mm,     # 0.3cm
                bottomMargin=8*mm   # 0.3cm
            )
            
            # Create enhanced styles for better layout matching
            styles = getSampleStyleSheet()
            
            # Company header style
            company_style = ParagraphStyle(
                'CompanyStyle',
                parent=styles['Normal'],
                fontSize=13,
                spaceAfter=3,
                spaceBefore=0,
                alignment=1,  # Center
                fontName='Helvetica-Bold'
            )
            
            # Payslip header style
            payslip_header_style = ParagraphStyle(
                'PayslipHeaderStyle',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6,
                spaceBefore=1,
                alignment=1,  # Center
                fontName='Helvetica-Bold'
            )
            
            # Employee info style
            info_style = ParagraphStyle(
                'InfoStyle',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=1,
                spaceBefore=1,
                fontName='Helvetica'
            )
            
            # Net salary style
            net_salary_style = ParagraphStyle(
                'NetSalaryStyle',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=2,
                spaceBefore=4,
                alignment=1,  # Center
                fontName='Helvetica-Bold'
            )
            
            # Amount in words style
            words_style = ParagraphStyle(
                'WordsStyle',
                parent=styles['Normal'],
                fontSize=8,
                spaceAfter=4,
                spaceBefore=2,
                alignment=1,  # Center
                fontName='Helvetica-Oblique'
            )
            
            # Parse HTML to extract payslip data
            story = generate_enhanced_reportlab_story(html_content, styles, company_style, 
                                                    payslip_header_style, info_style, 
                                                    net_salary_style, words_style)
            
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

def clean_html_for_server(html_content: str) -> str:
    """
    Clean HTML content for better server compatibility
    """
    # Remove problematic CSS properties
    problematic_properties = [
        'gap: 2%',
        'print-color-adjust: exact',
        '-webkit-print-color-adjust: exact',
        'margin: 0 1%;'  # Replace with explicit margins
    ]
    
    cleaned_html = html_content
    for prop in problematic_properties:
        cleaned_html = cleaned_html.replace(prop, '')
    
    # Add explicit font specifications for server environments
    font_css = """
        * {
            font-family: 'Arial', 'Helvetica', sans-serif !important;
        }
        
        .salary-details {
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
        }
        
        .earnings {
            width: 48%;
            margin-right: 2%;
        }
        
        .deductions {
            width: 48%;
            margin-left: 2%;
        }
    """
    
    # Insert font CSS before closing </style> tag
    if '</style>' in cleaned_html:
        cleaned_html = cleaned_html.replace('</style>', font_css + '\n    </style>')
    
    return cleaned_html

def generate_enhanced_reportlab_story(html_content: str, styles, company_style, 
                                    payslip_header_style, info_style, 
                                    net_salary_style, words_style):
    """
    Convert HTML content to ReportLab story with enhanced layout matching
    """
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    import re
    
    story = []
    
    # Parse HTML to extract payslip data
    # Split by payslip divs
    payslip_pattern = r'<div class="payslip">(.*?)</div>'
    payslips = re.findall(payslip_pattern, html_content, re.DOTALL)
    
    payslip_count = 0
    
    for payslip_html in payslips:
        payslip_count += 1
        
        # Extract company name
        story.append(Paragraph("SSPL CONSTRUCTIONS PVT LTD", company_style))
        
        # Extract payslip period
        period_match = re.search(r'PAYSLIP FOR ([A-Z]+ \d{4})', payslip_html)
        if period_match:
            period = period_match.group(1)
            story.append(Paragraph(f"PAYSLIP FOR {period}", payslip_header_style))
        
        # Add border spacer
        story.append(Spacer(1, 3*mm))
        
        # Extract employee information
        emp_info_data = []
        
        # Left column info
        emp_id_match = re.search(r'<strong>ID:</strong> (\w+)', payslip_html)
        name_match = re.search(r'<strong>Name:</strong> ([^<]+)', payslip_html)
        skill_match = re.search(r'<strong>Skill:</strong> ([^<]+)', payslip_html)
        days_match = re.search(r'<strong>Days:</strong> (\d+)', payslip_html)
        
        # Right column info
        dept_match = re.search(r'<strong>Dept:</strong> ([^<]+)', payslip_html)
        desig_match = re.search(r'<strong>Desig:</strong> ([^<]+)', payslip_html)
        rate_match = re.search(r'<strong>Rate:</strong> ([^<]+)', payslip_html)
        site_match = re.search(r'<strong>Site:</strong> ([^<]+)', payslip_html)
        
        # Create employee info table
        emp_data = [
            ['ID:', emp_id_match.group(1) if emp_id_match else 'N/A',
             'Dept:', dept_match.group(1) if dept_match else 'N/A'],
            ['Name:', name_match.group(1) if name_match else 'N/A',
             'Desig:', desig_match.group(1) if desig_match else 'N/A'],
            ['Skill:', skill_match.group(1) if skill_match else 'N/A',
             'Rate:', rate_match.group(1) if rate_match else 'N/A'],
            ['Days:', days_match.group(1) if days_match else 'N/A',
             'Site:', site_match.group(1) if site_match else 'N/A']
        ]
        
        emp_table = Table(emp_data, colWidths=[25*mm, 65*mm, 25*mm, 65*mm])
        emp_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
        ]))
        
        story.append(emp_table)
        story.append(Spacer(1, 4*mm))
        
        # Extract earnings and deductions tables
        earnings_data = [['EARNINGS', 'AMOUNT']]
        deductions_data = [['DEDUCTIONS', 'AMOUNT']]
        
        # Parse earnings
        earnings_pattern = r'<div class="earnings">.*?<table>(.*?)</table>'
        earnings_match = re.search(earnings_pattern, payslip_html, re.DOTALL)
        if earnings_match:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', earnings_match.group(1), re.DOTALL)
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row)
                if len(cells) >= 2:
                    # Clean HTML tags
                    cell1 = re.sub(r'<[^>]+>', '', cells[0]).strip()
                    cell2 = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    if cell1 and cell2:
                        earnings_data.append([cell1, cell2])
        
        # Parse deductions
        deductions_pattern = r'<div class="deductions">.*?<table>(.*?)</table>'
        deductions_match = re.search(deductions_pattern, payslip_html, re.DOTALL)
        if deductions_match:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', deductions_match.group(1), re.DOTALL)
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row)
                if len(cells) >= 2:
                    # Clean HTML tags
                    cell1 = re.sub(r'<[^>]+>', '', cells[0]).strip()
                    cell2 = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    if cell1 and cell2:
                        deductions_data.append([cell1, cell2])
        
        # Create earnings and deductions tables side by side
        earnings_table = Table(earnings_data, colWidths=[50*mm, 40*mm])
        earnings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            # Highlight total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        deductions_table = Table(deductions_data, colWidths=[50*mm, 40*mm])
        deductions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            # Highlight total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        # Combine tables side by side
        combined_data = [[earnings_table, deductions_table]]
        combined_table = Table(combined_data, colWidths=[90*mm, 90*mm])
        combined_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(combined_table)
        story.append(Spacer(1, 6*mm))
        
        # Extract net salary
        net_salary_match = re.search(r'NET SALARY: ([^<]+)', payslip_html)
        if net_salary_match:
            net_salary = net_salary_match.group(1).strip()
            story.append(Paragraph(f"NET SALARY: {net_salary}", net_salary_style))
        
        # Extract amount in words
        words_match = re.search(r'<strong>([^<]+Only)</strong>', payslip_html)
        if words_match:
            amount_words = words_match.group(1)
            story.append(Paragraph(amount_words, words_style))
        
        story.append(Spacer(1, 6*mm))
        
        # Add signature lines
        sig_data = [['Employee Signature', 'Employer Signature']]
        sig_table = Table(sig_data, colWidths=[90*mm, 90*mm])
        sig_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),  # Space for signature
            ('LINEBELOW', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(sig_table)
        
        # Add page break after every 3 payslips (except the last one)
        if payslip_count % 3 == 0 and payslip_count < len(payslips):
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 8*mm))  # Space between payslips on same page
    
    return story

# Example usage and testing
if __name__ == "__main__":
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            .payslip { border: 1px solid black; padding: 10px; margin: 10px; }
        </style>
    </head>
    <body>
        <div class="payslip">
            <h2>SSPL CONSTRUCTIONS PVT LTD</h2>
            <p>PAYSLIP FOR AUG 2025</p>
            <div class="employee-info">
                <p><strong>ID:</strong> 910001</p>
                <p><strong>Name:</strong> PRADIPTA DAS</p>
            </div>
            <div class="earnings">
                <table>
                    <tr><td>Basic</td><td>₹14,041.00</td></tr>
                    <tr><td>TOTAL</td><td>₹14,456.69</td></tr>
                </table>
            </div>
            <div class="deductions">
                <table>
                    <tr><td>PF</td><td>₹1,684.92</td></tr>
                    <tr><td>TOTAL</td><td>₹4,012.45</td></tr>
                </table>
            </div>
            <p><strong>NET SALARY: ₹10,444.24</strong></p>
            <p><strong>Ten Thousand Four Hundred Forty Four Only</strong></p>
        </div>
    </body>
    </html>
    """
    
    try:
        pdf_path = generate_payroll_pdf(sample_html, "test_payslip.pdf")
        print(f"PDF generated successfully at: {pdf_path}")
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")