from flask import flash, redirect, url_for
from app.calibration import bp


@bp.route('/')
def calibration():
    """Generate calibration PDFs for all paper sizes"""
    try:
        # Import and run calibration script
        import calibration
        flash('Calibration PDFs generated in calibration/ directory')
    except Exception as e:
        flash(f'Error generating calibration PDFs: {str(e)}')
    
    return redirect(url_for('main.index'))