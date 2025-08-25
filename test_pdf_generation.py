#!/usr/bin/env python3
"""
Test script to debug PDF generation issues on deployed server
"""

import os
import sys
import tempfile

def test_pdf_generation():
    """Test PDF generation with different libraries"""
    
    print("=== PDF Generation Test ===")
    
    # Test HTML content
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .header { text-align: center; color: navy; }
            .content { border: 1px solid black; padding: 20px; margin: 20px; }
        </style>
    </head>
    <body>
        <div class="content">
            <h1 class="header">Test PDF Generation</h1>
            <p>This is a test to verify PDF generation is working on the deployed server.</p>
            <p>Current working directory: {}</p>
            <p>Python version: {}</p>
        </div>
    </body>
    </html>
    """.format(os.getcwd(), sys.version)
    
    # Test 1: WeasyPrint
    print("\n1. Testing WeasyPrint...")
    try:
        from weasyprint import HTML
        print("✓ WeasyPrint imported successfully")
        
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        # Generate PDF
        HTML(string=test_html).write_pdf(pdf_path)
        
        if os.path.exists(pdf_path):
            file_size = os.path.getsize(pdf_path)
            print(f"✓ WeasyPrint PDF generated successfully: {pdf_path} ({file_size} bytes)")
            os.unlink(pdf_path)  # Clean up
        else:
            print("✗ WeasyPrint PDF file not created")
            
    except ImportError as e:
        print(f"✗ WeasyPrint not available: {e}")
    except Exception as e:
        print(f"✗ WeasyPrint failed: {e}")
    
    # Test 2: ReportLab
    print("\n2. Testing ReportLab...")
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        print("✓ ReportLab imported successfully")
        
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        # Generate PDF
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Test PDF Generation", styles['Title']),
            Paragraph("This is a test to verify ReportLab PDF generation.", styles['Normal'])
        ]
        doc.build(story)
        
        if os.path.exists(pdf_path):
            file_size = os.path.getsize(pdf_path)
            print(f"✓ ReportLab PDF generated successfully: {pdf_path} ({file_size} bytes)")
            os.unlink(pdf_path)  # Clean up
        else:
            print("✗ ReportLab PDF file not created")
            
    except ImportError as e:
        print(f"✗ ReportLab not available: {e}")
    except Exception as e:
        print(f"✗ ReportLab failed: {e}")
    
    # Test 3: System dependencies
    print("\n3. Testing system dependencies...")
    try:
        import ctypes
        import ctypes.util
        
        # Check for Cairo
        cairo_path = ctypes.util.find_library('cairo')
        if cairo_path:
            print(f"✓ Cairo library found: {cairo_path}")
        else:
            print("✗ Cairo library not found")
        
        # Check for Pango
        pango_path = ctypes.util.find_library('pango-1.0')
        if pango_path:
            print(f"✓ Pango library found: {pango_path}")
        else:
            print("✗ Pango library not found")
            
    except Exception as e:
        print(f"✗ System dependency check failed: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_pdf_generation()
