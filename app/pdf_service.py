"""
Optimized PDF generation service with streaming and caching support.
"""

import os
import io
import hashlib
import tempfile
import threading
from typing import Dict, Any, Optional, Generator, Tuple
from pathlib import Path
from PIL import Image
import pypdfium2 as pdfium
from flask import current_app, send_file, Response
from werkzeug.utils import secure_filename

from utilities import (
    CardSize, PaperSize, generate_pdf, 
    get_image_file_paths, delete_hidden_files_in_directory
)
from app.utils import create_temp_directories, save_uploaded_files, cleanup_temp_directory
from app.performance import monitor_memory_usage, optimize_image_processing


class PDFCache:
    """Simple in-memory cache for generated PDFs"""
    
    def __init__(self, max_size_mb: int = 100):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size = 0
        self.lock = threading.Lock()
    
    def _generate_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate a cache key from request data"""
        # Create a deterministic key from the request parameters
        key_data = {
            'card_size': request_data.get('card_size'),
            'paper_size': request_data.get('paper_size'),
            'only_fronts': request_data.get('only_fronts'),
            'crop': request_data.get('crop'),
            'extend_corners': request_data.get('extend_corners'),
            'ppi': request_data.get('ppi'),
            'quality': request_data.get('quality'),
            'skip_indices': sorted(request_data.get('skip_indices', [])),
            'load_offset': request_data.get('load_offset'),
            'name': request_data.get('name'),
            'file_hashes': self._get_file_hashes(request_data.get('files', {}))
        }
        
        # Create hash from sorted key data
        key_string = str(sorted(key_data.items()))
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_file_hashes(self, files: Dict[str, Any]) -> Dict[str, str]:
        """Generate hashes for uploaded files"""
        hashes = {}
        for file_type, file_list in files.items():
            if file_list:
                file_hashes = []
                for file in file_list:
                    if hasattr(file, 'read'):
                        file.seek(0)
                        content = file.read()
                        file_hashes.append(hashlib.md5(content).hexdigest())
                        file.seek(0)  # Reset file pointer
                hashes[file_type] = sorted(file_hashes)
        return hashes
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result"""
        with self.lock:
            if cache_key in self.cache:
                # Update access time
                self.cache[cache_key]['last_accessed'] = os.path.getmtime(self.cache[cache_key]['file_path'])
                return self.cache[cache_key]
        return None
    
    def set(self, cache_key: str, file_path: str, metadata: Dict[str, Any]):
        """Cache a result"""
        with self.lock:
            file_size = os.path.getsize(file_path)
            
            # Check if we need to evict old entries
            while self.current_size + file_size > self.max_size_bytes and self.cache:
                self._evict_oldest()
            
            self.cache[cache_key] = {
                'file_path': file_path,
                'file_size': file_size,
                'created_at': os.path.getmtime(file_path),
                'last_accessed': os.path.getmtime(file_path),
                'metadata': metadata
            }
            self.current_size += file_size
    
    def _evict_oldest(self):
        """Evict the least recently accessed cache entry"""
        if not self.cache:
            return
        
        oldest_key = min(self.cache.keys(), 
                        key=lambda k: self.cache[k]['last_accessed'])
        
        entry = self.cache[oldest_key]
        self.current_size -= entry['file_size']
        
        # Clean up the file
        try:
            if os.path.exists(entry['file_path']):
                os.remove(entry['file_path'])
        except OSError:
            pass
        
        del self.cache[oldest_key]


class StreamingPDFGenerator:
    """Generate PDFs with streaming support for large files"""
    
    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
    
    def generate_streaming_pdf(self, 
                             front_dir: str,
                             back_dir: str, 
                             double_sided_dir: str,
                             card_size: CardSize,
                             paper_size: PaperSize,
                             **kwargs) -> Generator[bytes, None, None]:
        """Generate PDF with streaming output"""
        
        # Create a temporary file for the PDF
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        
        try:
            # Generate PDF to temporary file
            generate_pdf(
                front_dir_path=front_dir,
                back_dir_path=back_dir,
                double_sided_dir_path=double_sided_dir,
                output_path=temp_path,
                card_size=card_size,
                paper_size=paper_size,
                **kwargs
            )
            
            # Stream the file in chunks
            with os.fdopen(temp_fd, 'rb') as f:
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except OSError:
                pass


class OptimizedPDFService:
    """Main service for optimized PDF generation"""
    
    def __init__(self):
        self.cache = PDFCache()
        self.streaming_generator = StreamingPDFGenerator()
        self.parallel_processing = True
        self.max_concurrent_tasks = 4
        self.active_tasks = 0
        self.task_lock = threading.Lock()
    
    def generate_pdf_optimized(self, 
                              request_data: Dict[str, Any],
                              files: Dict[str, Any],
                              use_cache: bool = True,
                              stream_output: bool = False) -> Dict[str, Any]:
        """Generate PDF with optimizations"""
        
        # Check cache first
        if use_cache:
            cache_key = self.cache._generate_cache_key({**request_data, 'files': files})
            cached_result = self.cache.get(cache_key)
            if cached_result:
                current_app.logger.info(f"Cache hit for key: {cache_key}")
                return {
                    'success': True,
                    'cached': True,
                    'file_path': cached_result['file_path'],
                    'metadata': cached_result['metadata']
                }
        
        # Check memory usage and optimize settings
        memory_usage = monitor_memory_usage()
        if memory_usage['percent'] > 85:
            current_app.logger.warning("High memory usage detected, using conservative settings")
            request_data = self._apply_memory_optimizations(request_data)
        
        # Create temporary directories
        temp_dir, front_dir, back_dir, double_sided_dir, output_dir, _ = create_temp_directories()
        
        try:
            # Save uploaded files with optimization
            self._save_files_optimized(files, front_dir, back_dir, double_sided_dir)
            
            # Generate output path
            output_path = os.path.join(output_dir, 'cards.pdf')
            
            # Apply image processing optimizations
            optimized_settings = optimize_image_processing()
            request_data.update(optimized_settings)
            
            # Generate PDF
            if stream_output:
                # For streaming, we'll generate to a temporary file first
                temp_pdf_path = os.path.join(output_dir, 'temp_cards.pdf')
                generate_pdf(
                    front_dir_path=front_dir,
                    back_dir_path=back_dir,
                    double_sided_dir_path=double_sided_dir,
                    output_path=temp_pdf_path,
                    card_size=CardSize(request_data.get('card_size', CardSize.STANDARD.value)),
                    paper_size=PaperSize(request_data.get('paper_size', PaperSize.LETTER.value)),
                    only_fronts=request_data.get('only_fronts', False),
                    crop_string=request_data.get('crop'),
                    extend_corners=request_data.get('extend_corners', 0),
                    ppi=request_data.get('ppi', 300),
                    quality=request_data.get('quality', 75),
                    skip_indices=request_data.get('skip_indices', []),
                    load_offset=request_data.get('load_offset', False),
                    name=request_data.get('name')
                )
                
                return {
                    'success': True,
                    'streaming': True,
                    'file_path': temp_pdf_path,
                    'temp_dir': temp_dir
                }
            else:
                generate_pdf(
                    front_dir_path=front_dir,
                    back_dir_path=back_dir,
                    double_sided_dir_path=double_sided_dir,
                    output_path=output_path,
                    card_size=CardSize(request_data.get('card_size', CardSize.STANDARD.value)),
                    paper_size=PaperSize(request_data.get('paper_size', PaperSize.LETTER.value)),
                    only_fronts=request_data.get('only_fronts', False),
                    crop_string=request_data.get('crop'),
                    extend_corners=request_data.get('extend_corners', 0),
                    ppi=request_data.get('ppi', 300),
                    quality=request_data.get('quality', 75),
                    skip_indices=request_data.get('skip_indices', []),
                    load_offset=request_data.get('load_offset', False),
                    name=request_data.get('name')
                )
                
                # Cache the result
                if use_cache:
                    cache_key = self.cache._generate_cache_key({**request_data, 'files': files})
                    metadata = {
                        'file_size': os.path.getsize(output_path),
                        'generated_at': os.path.getmtime(output_path),
                        'request_params': request_data
                    }
                    self.cache.set(cache_key, output_path, metadata)
                
                return {
                    'success': True,
                    'file_path': output_path,
                    'temp_dir': temp_dir,
                    'file_size': os.path.getsize(output_path)
                }
                
        except Exception as e:
            # Clean up on error
            cleanup_temp_directory(temp_dir)
            raise e
    
    def _apply_memory_optimizations(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply memory optimizations to request data"""
        optimized = request_data.copy()
        
        # Reduce quality for high memory usage
        if optimized.get('quality', 75) > 60:
            optimized['quality'] = 60
        
        # Reduce PPI for high memory usage
        if optimized.get('ppi', 300) > 200:
            optimized['ppi'] = 200
        
        return optimized
    
    def _save_files_optimized(self, files: Dict[str, Any], front_dir: str, back_dir: str, double_sided_dir: str):
        """Save uploaded files with optimizations"""
        
        # Process files in parallel if possible
        if self.parallel_processing and len(files) > 1:
            threads = []
            
            if 'front_files' in files:
                thread = threading.Thread(
                    target=save_uploaded_files,
                    args=(files['front_files'], front_dir)
                )
                threads.append(thread)
                thread.start()
            
            if 'back_files' in files:
                thread = threading.Thread(
                    target=save_uploaded_files,
                    args=(files['back_files'], back_dir)
                )
                threads.append(thread)
                thread.start()
            
            if 'double_sided_files' in files:
                thread = threading.Thread(
                    target=save_uploaded_files,
                    args=(files['double_sided_files'], double_sided_dir)
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
        else:
            # Sequential processing
            if 'front_files' in files:
                save_uploaded_files(files['front_files'], front_dir)
            if 'back_files' in files:
                save_uploaded_files(files['back_files'], back_dir)
            if 'double_sided_files' in files:
                save_uploaded_files(files['double_sided_files'], double_sided_dir)
    
    def create_streaming_response(self, file_path: str, filename: str = 'cards.pdf') -> Response:
        """Create a streaming response for large PDF files"""
        
        def generate():
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        
        response = Response(generate(), mimetype='application/pdf')
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = str(os.path.getsize(file_path))
        
        return response
    
    def cleanup_cache(self):
        """Clean up old cache entries"""
        self.cache.cleanup_old_tasks()


# Global service instance
pdf_service = OptimizedPDFService()
