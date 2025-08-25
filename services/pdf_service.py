import os
import tempfile
from pathlib import Path
from typing import Optional

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
        # Try WeasyPrint first
        try:
            from weasyprint import HTML, CSS
            HTML(string=html_content).write_pdf(temp_pdf_path)
            return temp_pdf_path
            
        except ImportError:
            # Fallback to ReportLab
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.platypus import SimpleDocTemplate, Paragraph
                from reportlab.lib.styles import getSampleStyleSheet
                
                # Create PDF with ReportLab
                doc = SimpleDocTemplate(temp_pdf_path, pagesize=A4)
                styles = getSampleStyleSheet()
                
                # Convert HTML to basic text
                # Note: This is a very simplified conversion
                text = html_content.replace('<br>', '\n')
                text = ''.join([i if ord(i) < 128 else ' ' for i in text])
                
                # Create story with paragraphs
                story = []
                story.append(Paragraph("PDF generated with ReportLab (Limited HTML Support)", 
                                    styles['Title']))
                story.append(Paragraph(text, styles['Normal']))
                
                # Build PDF
                doc.build(story)
                return temp_pdf_path
                
            except ImportError:
                raise ImportError(
                    "Neither WeasyPrint nor ReportLab is available. "
                    "Please install one of them: \n"
                    "pip install weasyprint\n"
                    "- or -\n"
                    "pip install reportlab"
                )
                
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        raise e

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