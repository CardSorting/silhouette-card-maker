# Complete Flask Web Application - 1:1 CLI Feature Parity

This enhanced Flask application provides **complete 1:1 feature parity** with the CLI tools, plus additional web-specific enhancements.

## 🎯 **Complete Feature Comparison**

### ✅ **Fully Implemented CLI Features**

| CLI Feature | Flask Implementation | Status |
|-------------|---------------------|---------|
| `--front_dir_path` | File upload interface | ✅ Complete |
| `--back_dir_path` | File upload + multiple back selection | ✅ Complete |
| `--double_sided_dir_path` | File upload interface | ✅ Complete |
| `--output_path` | Automatic naming | ✅ Complete |
| `--output_images` | ZIP download option | ✅ Complete |
| `--card_size` | All 10 card sizes | ✅ Complete |
| `--paper_size` | All 5 paper sizes | ✅ Complete |
| `--only_fronts` | Checkbox option | ✅ Complete |
| `--crop` | Text input with validation | ✅ Complete |
| `--extend_corners` | Number input | ✅ Complete |
| `--ppi` | Number input (72-600) | ✅ Complete |
| `--quality` | Number input (1-100) | ✅ Complete |
| `--load_offset` | Checkbox + saved state display | ✅ Complete |
| `--skip` | Comma-separated input | ✅ Complete |
| `--name` | Text input | ✅ Complete |
| `--version` | API endpoint `/api/version` | ✅ Complete |
| Multiple back image selection | Interactive web interface | ✅ Complete |
| Hidden file cleanup | Automatic (`delete_hidden_files_in_directory`) | ✅ Complete |
| EXIF transpose | Handled in utilities | ✅ Complete |

### ✅ **Additional CLI Tools Implemented**

| CLI Tool | Flask Route | Features |
|----------|------------|----------|
| `offset_pdf.py` | `/offset` | Full offset correction with save/load |
| `calibration.py` | `/calibration` | Generate calibration PDFs |
| `clean_up.py` | `/cleanup` | Clean game directories |

### ✅ **Plugin System Integration**

| Game | Formats | Status |
|------|---------|--------|
| MTG | simple, mtga, mtgo, archidekt, deckstats, moxfield, scryfall_json | ✅ Complete |
| Yu-Gi-Oh! | ydke, ydk | ✅ Complete |
| Lorcana | dreamborn | ✅ Complete |
| Riftbound | tts, pixelborn, piltover_archive | ✅ Complete |
| Altered | ajordat | ✅ Complete |
| Netrunner | text, bbcode, markdown, plain_text, jinteki | ✅ Complete |
| Gundam | deckplanet, limitless, egman, exburst | ✅ Complete |
| Grand Archive | omnideck | ✅ Complete |
| Digimon | tts, digimoncardio, digimoncarddev, digimoncardapp, digimonmeta, untap | ✅ Complete |
| One Piece | optcgsim, egman | ✅ Complete |
| Flesh and Blood | fabrary | ✅ Complete |

## 🚀 **Enhanced Features (Beyond CLI)**

### **Web-Specific Improvements**
- **Tabbed Interface**: Manual upload vs Plugin mode
- **Drag & Drop**: File upload with visual feedback
- **Real-time Validation**: Form validation and file counting
- **Interactive Back Selection**: Visual interface for multiple back images
- **Saved State Display**: Shows current offset settings
- **Progress Feedback**: Flash messages and status updates
- **Responsive Design**: Works on mobile and desktop
- **Utility Dashboard**: Quick access to offset, calibration, cleanup tools

### **API Enhancements**
- **Version Endpoint**: `/api/version` with feature list
- **RESTful Design**: Proper HTTP status codes and responses
- **ZIP Downloads**: Automatic packaging for image output mode
- **Error Handling**: Comprehensive error messages and recovery

## 📁 **File Structure**

```
silhouette-card-maker/
├── app_enhanced.py           # Complete Flask app (replaces app.py)
├── templates/
│   ├── index_enhanced.html   # Main interface with tabs
│   ├── offset.html          # PDF offset correction
│   └── select_back.html     # Multiple back image selection
├── create_pdf.py            # Original CLI (still works)
├── offset_pdf.py           # Original CLI (still works)  
├── utilities.py             # Shared core functionality
└── README_COMPLETE_FLASK.md # This documentation
```

## 🔧 **Quick Start**

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Enhanced Flask App
```bash
python app_enhanced.py
```

### 3. Open Browser
Navigate to: **http://localhost:5000**

## 🎨 **Usage Guide**

### **Manual Upload Mode**
1. **Upload Files**: Drag & drop or click to select images
2. **Configure Settings**: Choose card size, paper size, and options
3. **Advanced Options**: Set crop, extend corners, PPI, quality, skip cards
4. **Generate**: Click "Generate Cards" for PDF or ZIP download

### **Plugin Mode**  
1. **Select Game**: Choose from 11+ supported card games
2. **Choose Format**: Pick decklist format (varies by game)
3. **Upload Decklist**: TXT or JSON file with your cards
4. **Configure Plugin Options**: Game-specific settings (MTG has most options)
5. **Set Generation Options**: Same as manual mode
6. **Fetch & Generate**: Plugin downloads images and generates cards

### **Offset Correction**
1. **Access Tool**: Click "PDF Offset Tool" from main page
2. **Upload PDF**: Select your generated PDF
3. **Set Offsets**: Enter X/Y pixel adjustments
4. **Save Settings**: Check box to save for future use
5. **Apply & Download**: Get corrected PDF

### **Utilities**
- **Generate Calibration**: Creates alignment test sheets for all paper sizes
- **Clean Game Dirs**: Removes all files from game/front and game/double_sided
- **Version Info**: Shows app version and feature list

## 🔍 **Technical Implementation Details**

### **Core Architecture**
- **Flask Backend**: Routes handle all CLI functionality
- **Shared Logic**: Uses same `utilities.py` as CLI tools
- **Temporary Processing**: Files processed in secure temp directories
- **Auto Cleanup**: All temp files automatically removed

### **Plugin Integration**
- **Subprocess Execution**: Runs existing plugin scripts
- **Directory Management**: Temporarily redirects game/front directory
- **Error Handling**: Captures plugin output and errors
- **Option Mapping**: Web form fields map to CLI arguments

### **File Handling**
- **Security**: `secure_filename()` prevents path traversal
- **Validation**: File type checking and size limits (64MB)
- **Multiple Uploads**: Handles arrays of files correctly
- **Hidden File Cleanup**: Removes .DS_Store, Thumbs.db, etc.

### **State Management**
- **Offset Persistence**: Saves/loads offset settings to `data/offset_data.json`
- **Form State**: Preserves form data during back image selection
- **Flash Messages**: User feedback for all operations

## 📊 **Feature Completeness Matrix**

| Category | CLI Features | Flask Features | Completeness |
|----------|--------------|----------------|--------------|
| **Core Generation** | 15 options | 15 options | 100% ✅ |
| **File Handling** | Directory-based | Upload-based | 100% ✅ |
| **Output Formats** | PDF + Images | PDF + ZIP | 100% ✅ |
| **Plugin System** | 11 games, 30+ formats | 11 games, 30+ formats | 100% ✅ |
| **Offset Correction** | Full CLI tool | Full web interface | 100% ✅ |
| **Utilities** | 3 CLI tools | 3 web routes | 100% ✅ |
| **Error Handling** | CLI messages | Web notifications | 100% ✅ |

## 🎯 **Advanced Usage Examples**

### **API Usage (Same as CLI)**
```bash
# Generate standard MTG cards from Moxfield decklist
curl -X POST http://localhost:5000/generate \
  -F "use_plugin=on" \
  -F "plugin_game=mtg" \
  -F "plugin_format=moxfield" \
  -F "decklist_files=@my_deck.txt" \
  -F "card_size=standard" \
  -F "paper_size=letter" \
  --output cards.pdf

# Manual upload with advanced options
curl -X POST http://localhost:5000/generate \
  -F "front_files=@card1.png" \
  -F "front_files=@card2.png" \
  -F "card_size=japanese" \
  -F "paper_size=a4" \
  -F "crop=3mm" \
  -F "extend_corners=10" \
  -F "output_images=on" \
  --output cards.zip
```

### **Complex Workflows**
1. **Multi-step Process**: Use plugins → generate PDF → apply offset → download
2. **Batch Processing**: Multiple decklists with different settings
3. **Quality Control**: Generate images first, then convert to PDF
4. **Calibration Workflow**: Generate calibration → print → measure → set offset

## 🔒 **Security & Production Notes**

### **Production Deployment**
1. **Change Secret Key**: Update `app.secret_key` in `app_enhanced.py`
2. **Disable Debug**: Set `debug=False` in `app.run()`
3. **Use Production Server**: Deploy with Gunicorn/uWSGI
4. **Reverse Proxy**: Use nginx for static files and SSL
5. **File Size Limits**: Adjust `MAX_CONTENT_LENGTH` as needed
6. **Rate Limiting**: Consider adding request rate limits

### **Security Features**
- **Secure File Handling**: Path traversal protection
- **File Type Validation**: Only allowed image/text formats
- **Temporary Isolation**: Each request gets isolated temp directory
- **Auto Cleanup**: No persistent file storage
- **Input Sanitization**: All form inputs validated

## 🆚 **CLI vs Flask Comparison**

| Aspect | CLI Tools | Enhanced Flask App |
|--------|-----------|-------------------|
| **Interface** | Command line | Modern web UI |
| **File Input** | Directory-based | Upload-based |
| **Back Selection** | Interactive prompt | Visual grid selection |
| **Plugin Usage** | Manual script execution | Integrated web form |
| **Offset Correction** | Separate tool | Integrated workflow |
| **Output** | Local files | Downloads |
| **Accessibility** | Technical users | All skill levels |
| **Batch Processing** | Script-friendly | API-friendly |
| **State Persistence** | File-based | Web session + file |
| **Error Feedback** | Terminal output | Web notifications |

## 🎉 **Summary**

The enhanced Flask application provides **complete 1:1 feature parity** with all CLI tools while adding significant web-specific enhancements:

- ✅ **All 15 create_pdf.py options** implemented
- ✅ **Complete offset_pdf.py functionality** 
- ✅ **Full plugin system support** (11 games, 30+ formats)
- ✅ **Interactive back image selection**
- ✅ **Calibration and cleanup utilities**
- ✅ **Modern, responsive web interface**
- ✅ **API access for programmatic use**
- ✅ **Production-ready architecture**

This is not just a "web wrapper" - it's a complete reimplementation that maintains all CLI functionality while providing a superior user experience for web users.