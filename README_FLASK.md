# Flask Web Application for Silhouette Card Maker

This is a Flask web application version of the Silhouette Card Maker CLI tool. It provides a user-friendly web interface for creating card PDFs with registration marks for silhouette cutting machines.

## Features

- **Web Interface**: Easy-to-use form-based interface
- **File Upload**: Upload multiple card images directly through the browser
- **All CLI Options**: Access to all the original CLI functionality
- **API Endpoint**: Programmatic access via REST API
- **Real-time Feedback**: File selection feedback and error messages
- **Mobile Friendly**: Responsive design that works on mobile devices

## Quick Start

### 1. Install Dependencies

Make sure you have Python 3.7+ installed, then install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Run the Application

Start the Flask development server:

```bash
python app.py
```

The application will be available at: **http://localhost:5000**

### 3. Use the Web Interface

1. Open your browser and go to http://localhost:5000
2. Upload your card images:
   - **Front Images**: Required - select all your front card images
   - **Back Images**: Optional - select one image to use as the back for all cards
   - **Double-Sided Back Images**: Optional - select back images for double-sided cards (filenames must match front images)
3. Configure settings:
   - Choose card size (Standard, Japanese, Poker, etc.)
   - Choose paper size (Letter, A4, Tabloid, etc.)
   - Adjust advanced options as needed
4. Click "Generate PDF" to download your cards

## API Usage

You can also use the API endpoint for programmatic access:

```bash
curl -X POST http://localhost:5000/api/generate \
  -F "front_files=@card1.jpg" \
  -F "front_files=@card2.jpg" \
  -F "card_size=standard" \
  -F "paper_size=letter" \
  --output cards.pdf
```

### API Parameters

All the same parameters from the CLI are supported:

- `card_size`: standard, japanese, poker, bridge, tarot, etc.
- `paper_size`: letter, a4, tabloid, a3, archb
- `only_fronts`: true/false
- `crop`: e.g., "3mm", "0.125in", "6.5"
- `extend_corners`: integer (0+)
- `ppi`: integer (72-600)
- `quality`: integer (1-100)
- `skip_indices`: array of integers
- `name`: string

## Configuration

### Production Deployment

For production use, you should:

1. **Change the Secret Key**: Edit `app.py` and change the `secret_key`
2. **Use a Production Server**: Use Gunicorn, uWSGI, or another WSGI server
3. **Configure Environment**: Set `debug=False` and configure proper logging
4. **Reverse Proxy**: Use nginx or Apache as a reverse proxy
5. **File Upload Limits**: Adjust `MAX_CONTENT_LENGTH` if needed

### Example Production Setup with Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## File Upload Limits

- Maximum file size: 16MB per file
- Supported formats: PNG, JPG, JPEG, GIF, BMP, TIFF, WebP
- Multiple files can be uploaded simultaneously

## Differences from CLI Version

### Added Features
- Web-based user interface
- File upload handling
- Real-time form validation
- API endpoint for programmatic access
- Better error handling and user feedback

### Limitations
- No plugin system integration (yet)
- No interactive back image selection (uses first uploaded back image)
- Temporary file cleanup (files are automatically deleted after processing)

## Troubleshooting

### Common Issues

**"No module named 'X'"**
- Run `pip install -r requirements.txt` to install all dependencies

**"File too large" error**
- Files must be under 16MB. Resize images or adjust `MAX_CONTENT_LENGTH` in `app.py`

**"No front images provided"**
- Make sure you've selected at least one front image file

**Application won't start**
- Check that all dependencies are installed
- Ensure no other application is using port 5000
- Check the terminal for detailed error messages

### Development Mode

The app runs in debug mode by default, which provides:
- Automatic reloading when code changes
- Detailed error messages
- Interactive debugger in the browser

For production, set `debug=False` in the `app.run()` call.

## Original CLI Tool

The original CLI tool (`create_pdf.py`) is still available and fully functional. The Flask app is an additional interface that uses the same underlying logic.

## Support

For issues specific to the Flask web interface, please check the console output and browser developer tools for error messages. For general card-making questions, refer to the main project documentation.