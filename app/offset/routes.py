import os
import tempfile
from flask import render_template, request, send_file, flash, redirect, url_for
import pypdfium2 as pdfium

from app.offset import bp
from app.utils import cleanup_temp_directory
from utilities import load_saved_offset, save_offset, offset_images


@bp.route('/', methods=['GET', 'POST'])
def offset_pdf():
    """Handle PDF offset functionality"""
    if request.method == 'GET':
        # Show dedicated offset page
        saved_offset = load_saved_offset()
        return render_template('offset.html', saved_offset=saved_offset)
    
    temp_dir = None
    try:
        # Get form data
        pdf_file = request.files.get('pdf_file')
        x_offset = request.form.get('x_offset', type=int, default=0)
        y_offset = request.form.get('y_offset', type=int, default=0)
        save_offsets = request.form.get('save_offsets') == 'on'
        ppi = int(request.form.get('ppi', 300))
        
        if not pdf_file or not pdf_file.filename:
            flash('Please upload a PDF file.')
            return redirect(url_for('offset.offset_pdf'))
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        input_pdf_path = os.path.join(temp_dir, 'input.pdf')
        output_pdf_path = os.path.join(temp_dir, 'output_offset.pdf')
        
        # Save uploaded PDF
        pdf_file.save(input_pdf_path)
        
        # Load saved offset if available
        new_x_offset = 0
        new_y_offset = 0
        
        saved_offset = load_saved_offset()
        if saved_offset is not None:
            new_x_offset = saved_offset.x_offset
            new_y_offset = saved_offset.y_offset
        
        # Use provided offsets
        if x_offset is not None:
            new_x_offset = x_offset
        if y_offset is not None:
            new_y_offset = y_offset
        
        # Save new offset if requested
        if save_offsets:
            save_offset(new_x_offset, new_y_offset)
            flash(f'Saved offset: x={new_x_offset}, y={new_y_offset}')
        
        # Process PDF
        pdf = pdfium.PdfDocument(input_pdf_path)
        
        # Get all the raw page images from the PDF
        raw_images = []
        for page_number in range(len(pdf)):
            page = pdf.get_page(page_number)
            raw_images.append(page.render(ppi/72).to_pil())
        
        # Offset images
        final_images = offset_images(raw_images, new_x_offset, new_y_offset, ppi)
        
        # Save offset PDF
        final_images[0].save(output_pdf_path, save_all=True, append_images=final_images[1:], 
                           resolution=ppi, speed=0, subsampling=0, quality=100)
        
        # Return the offset PDF
        return send_file(output_pdf_path, 
                        as_attachment=True, 
                        download_name='cards_offset.pdf',
                        mimetype='application/pdf')
    
    except Exception as e:
        flash(f'Error processing PDF: {str(e)}')
        return redirect(url_for('offset.offset_pdf'))
    
    finally:
        cleanup_temp_directory(temp_dir)