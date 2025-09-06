"""
Enhanced validation and error handling for the PDF generation API.
"""

import os
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from PIL import Image
from flask import current_app

from utilities import CardSize, PaperSize


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message: str, code: str = None, field: str = None):
        self.message = message
        self.code = code or 'VALIDATION_ERROR'
        self.field = field
        super().__init__(self.message)


class PDFGenerationValidator:
    """Comprehensive validator for PDF generation requests"""
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
    MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB total
    
    # Parameter ranges
    PPI_RANGE = (72, 600)
    QUALITY_RANGE = (1, 100)
    EXTEND_CORNERS_RANGE = (0, 50)
    OFFSET_RANGE = (-1000, 1000)
    
    def __init__(self):
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[str] = []
    
    def validate_request(self, request_data: Dict[str, Any], files: Dict[str, Any]) -> Tuple[bool, List[Dict[str, str]]]:
        """Validate a complete PDF generation request"""
        self.errors = []
        self.warnings = []
        
        # Validate basic parameters
        self._validate_basic_parameters(request_data)
        
        # Validate file uploads
        self._validate_file_uploads(files)
        
        # Validate parameter combinations
        self._validate_parameter_combinations(request_data)
        
        # Check system resources
        self._validate_system_resources(request_data, files)
        
        return len(self.errors) == 0, self.errors
    
    def _validate_basic_parameters(self, request_data: Dict[str, Any]):
        """Validate basic request parameters"""
        
        # Card size validation
        try:
            card_size = request_data.get('card_size', CardSize.STANDARD.value)
            CardSize(card_size)
        except ValueError:
            self.errors.append({
                'field': 'card_size',
                'code': 'INVALID_CARD_SIZE',
                'message': f'Invalid card size: {card_size}. Must be one of: {[s.value for s in CardSize]}'
            })
        
        # Paper size validation
        try:
            paper_size = request_data.get('paper_size', PaperSize.LETTER.value)
            PaperSize(paper_size)
        except ValueError:
            self.errors.append({
                'field': 'paper_size',
                'code': 'INVALID_PAPER_SIZE',
                'message': f'Invalid paper size: {paper_size}. Must be one of: {[s.value for s in PaperSize]}'
            })
        
        # PPI validation
        try:
            ppi = int(request_data.get('ppi', 300))
            if not (self.PPI_RANGE[0] <= ppi <= self.PPI_RANGE[1]):
                self.errors.append({
                    'field': 'ppi',
                    'code': 'INVALID_PPI',
                    'message': f'PPI must be between {self.PPI_RANGE[0]} and {self.PPI_RANGE[1]}'
                })
        except (ValueError, TypeError):
            self.errors.append({
                'field': 'ppi',
                'code': 'INVALID_PPI_TYPE',
                'message': 'PPI must be a valid integer'
            })
        
        # Quality validation
        try:
            quality = int(request_data.get('quality', 75))
            if not (self.QUALITY_RANGE[0] <= quality <= self.QUALITY_RANGE[1]):
                self.errors.append({
                    'field': 'quality',
                    'code': 'INVALID_QUALITY',
                    'message': f'Quality must be between {self.QUALITY_RANGE[0]} and {self.QUALITY_RANGE[1]}'
                })
        except (ValueError, TypeError):
            self.errors.append({
                'field': 'quality',
                'code': 'INVALID_QUALITY_TYPE',
                'message': 'Quality must be a valid integer'
            })
        
        # Extend corners validation
        try:
            extend_corners = int(request_data.get('extend_corners', 0))
            if not (self.EXTEND_CORNERS_RANGE[0] <= extend_corners <= self.EXTEND_CORNERS_RANGE[1]):
                self.errors.append({
                    'field': 'extend_corners',
                    'code': 'INVALID_EXTEND_CORNERS',
                    'message': f'Extend corners must be between {self.EXTEND_CORNERS_RANGE[0]} and {self.EXTEND_CORNERS_RANGE[1]}'
                })
        except (ValueError, TypeError):
            self.errors.append({
                'field': 'extend_corners',
                'code': 'INVALID_EXTEND_CORNERS_TYPE',
                'message': 'Extend corners must be a valid integer'
            })
        
        # Skip indices validation
        skip_indices = request_data.get('skip_indices', [])
        if skip_indices:
            try:
                if not isinstance(skip_indices, list):
                    raise TypeError("Skip indices must be a list")
                
                for idx in skip_indices:
                    if not isinstance(idx, int) or idx < 0:
                        raise ValueError(f"Invalid skip index: {idx}")
                        
            except (ValueError, TypeError) as e:
                self.errors.append({
                    'field': 'skip_indices',
                    'code': 'INVALID_SKIP_INDICES',
                    'message': str(e)
                })
        
        # Name validation
        name = request_data.get('name', '')
        if name and not self._is_valid_filename(name):
            self.errors.append({
                'field': 'name',
                'code': 'INVALID_NAME',
                'message': 'Name contains invalid characters for filename'
            })
        
        # Crop validation
        crop = request_data.get('crop', '')
        if crop and not self._is_valid_crop_string(crop):
            self.errors.append({
                'field': 'crop',
                'code': 'INVALID_CROP',
                'message': 'Invalid crop format. Use format like "3mm", "0.125in", or "6.5"'
            })
    
    def _validate_file_uploads(self, files: Dict[str, Any]):
        """Validate uploaded files"""
        
        # Check if we have any files
        total_files = sum(len(file_list) for file_list in files.values() if file_list)
        if total_files == 0:
            self.errors.append({
                'field': 'files',
                'code': 'NO_FILES',
                'message': 'No files provided'
            })
            return
        
        # Check front files specifically
        front_files = files.get('front_files', [])
        if not front_files or not any(f.filename for f in front_files):
            self.errors.append({
                'field': 'front_files',
                'code': 'NO_FRONT_FILES',
                'message': 'At least one front image is required'
            })
        
        # Validate individual files
        total_size = 0
        for file_type, file_list in files.items():
            if not file_list:
                continue
                
            for file in file_list:
                if not file.filename:
                    continue
                
                # Check file extension
                if not self._is_allowed_file(file.filename):
                    self.errors.append({
                        'field': f'{file_type}',
                        'code': 'INVALID_FILE_TYPE',
                        'message': f'File {file.filename} has invalid extension. Allowed: {", ".join(self.ALLOWED_EXTENSIONS)}'
                    })
                    continue
                
                # Check file size
                try:
                    file.seek(0, 2)  # Seek to end
                    file_size = file.tell()
                    file.seek(0)  # Reset to beginning
                    
                    if file_size > self.MAX_FILE_SIZE:
                        self.errors.append({
                            'field': f'{file_type}',
                            'code': 'FILE_TOO_LARGE',
                            'message': f'File {file.filename} is too large. Maximum size: {self.MAX_FILE_SIZE / (1024*1024):.1f}MB'
                        })
                        continue
                    
                    total_size += file_size
                    
                except Exception as e:
                    self.errors.append({
                        'field': f'{file_type}',
                        'code': 'FILE_SIZE_ERROR',
                        'message': f'Could not determine size of file {file.filename}: {str(e)}'
                    })
        
        # Check total size
        if total_size > self.MAX_TOTAL_SIZE:
            self.errors.append({
                'field': 'files',
                'code': 'TOTAL_SIZE_TOO_LARGE',
                'message': f'Total upload size ({total_size / (1024*1024):.1f}MB) exceeds limit ({self.MAX_TOTAL_SIZE / (1024*1024):.1f}MB)'
            })
    
    def _validate_parameter_combinations(self, request_data: Dict[str, Any]):
        """Validate parameter combinations for logical consistency"""
        
        only_fronts = request_data.get('only_fronts', False)
        load_offset = request_data.get('load_offset', False)
        
        # If only fronts is true, load_offset should be false
        if only_fronts and load_offset:
            self.warnings.append("Load offset is ignored when only_fronts is true")
        
        # Check for potentially problematic combinations
        ppi = int(request_data.get('ppi', 300))
        quality = int(request_data.get('quality', 75))
        
        if ppi > 400 and quality > 90:
            self.warnings.append("High PPI and quality combination may result in very large files")
        
        if ppi < 150 and quality < 50:
            self.warnings.append("Low PPI and quality combination may result in poor output quality")
    
    def _validate_system_resources(self, request_data: Dict[str, Any], files: Dict[str, Any]):
        """Validate system resources and provide warnings"""
        
        # Count total files
        total_files = sum(len(file_list) for file_list in files.values() if file_list)
        
        # Estimate processing requirements
        ppi = int(request_data.get('ppi', 300))
        estimated_memory_mb = total_files * (ppi / 300) * 2  # Rough estimate
        
        if estimated_memory_mb > 500:
            self.warnings.append(f"Large request detected. Estimated memory usage: {estimated_memory_mb:.0f}MB")
        
        if total_files > 200:
            self.warnings.append(f"Large number of files ({total_files}). Consider using async generation.")
    
    def _is_allowed_file(self, filename: str) -> bool:
        """Check if file has allowed extension"""
        if not filename:
            return False
        
        ext = Path(filename).suffix.lower()
        return ext in self.ALLOWED_EXTENSIONS
    
    def _is_valid_filename(self, name: str) -> bool:
        """Check if name is valid for filename"""
        if not name:
            return True
        
        # Check for invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, name):
            return False
        
        # Check length
        if len(name) > 100:
            return False
        
        return True
    
    def _is_valid_crop_string(self, crop: str) -> bool:
        """Validate crop string format"""
        if not crop:
            return True
        
        # Patterns: "3mm", "0.125in", "6.5"
        patterns = [
            r'^\d+(\.\d+)?mm$',  # millimeters
            r'^\d+(\.\d+)?in$',  # inches
            r'^\d+(\.\d+)?$'     # raw number
        ]
        
        return any(re.match(pattern, crop.strip()) for pattern in patterns)


class OffsetValidator:
    """Validator for PDF offset requests"""
    
    def __init__(self):
        self.errors: List[Dict[str, str]] = []
    
    def validate_offset_request(self, request_data: Dict[str, Any], pdf_file) -> Tuple[bool, List[Dict[str, str]]]:
        """Validate PDF offset request"""
        self.errors = []
        
        # Validate PDF file
        if not pdf_file or not pdf_file.filename:
            self.errors.append({
                'field': 'pdf_file',
                'code': 'NO_PDF_FILE',
                'message': 'PDF file is required'
            })
            return len(self.errors) == 0, self.errors
        
        # Check file extension
        if not pdf_file.filename.lower().endswith('.pdf'):
            self.errors.append({
                'field': 'pdf_file',
                'code': 'INVALID_PDF_FILE',
                'message': 'File must be a PDF'
            })
        
        # Validate offset parameters
        try:
            x_offset = int(request_data.get('x_offset', 0))
            if not (-1000 <= x_offset <= 1000):
                self.errors.append({
                    'field': 'x_offset',
                    'code': 'INVALID_X_OFFSET',
                    'message': 'X offset must be between -1000 and 1000'
                })
        except (ValueError, TypeError):
            self.errors.append({
                'field': 'x_offset',
                'code': 'INVALID_X_OFFSET_TYPE',
                'message': 'X offset must be a valid integer'
            })
        
        try:
            y_offset = int(request_data.get('y_offset', 0))
            if not (-1000 <= y_offset <= 1000):
                self.errors.append({
                    'field': 'y_offset',
                    'code': 'INVALID_Y_OFFSET',
                    'message': 'Y offset must be between -1000 and 1000'
                })
        except (ValueError, TypeError):
            self.errors.append({
                'field': 'y_offset',
                'code': 'INVALID_Y_OFFSET_TYPE',
                'message': 'Y offset must be a valid integer'
            })
        
        try:
            ppi = int(request_data.get('ppi', 300))
            if not (72 <= ppi <= 600):
                self.errors.append({
                    'field': 'ppi',
                    'code': 'INVALID_PPI',
                    'message': 'PPI must be between 72 and 600'
                })
        except (ValueError, TypeError):
            self.errors.append({
                'field': 'ppi',
                'code': 'INVALID_PPI_TYPE',
                'message': 'PPI must be a valid integer'
            })
        
        return len(self.errors) == 0, self.errors


def validate_image_file(file_path: str) -> Tuple[bool, str]:
    """Validate that a file is a valid image"""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True, ""
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"


def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get detailed information about a file"""
    try:
        stat = os.stat(file_path)
        info = {
            'size': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'modified': stat.st_mtime,
            'is_image': False,
            'image_info': None
        }
        
        # Try to get image information
        try:
            with Image.open(file_path) as img:
                info['is_image'] = True
                info['image_info'] = {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height
                }
        except:
            pass
        
        return info
        
    except OSError as e:
        return {'error': str(e)}
