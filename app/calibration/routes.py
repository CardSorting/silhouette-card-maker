from flask import flash, redirect, url_for, render_template
from app.calibration import bp


@bp.route('/', methods=['GET', 'POST'])
def calibration():
    """Generate calibration PDFs for all paper sizes"""
    if request.method == 'GET':
        return render_template('calibration.html')
    
    try:
        # Import and run calibration script
        import calibration
        flash('Calibration PDFs generated in calibration/ directory')
    except Exception as e:
        flash(f'Error generating calibration PDFs: {str(e)}')
    
    return redirect(url_for('calibration.calibration'))