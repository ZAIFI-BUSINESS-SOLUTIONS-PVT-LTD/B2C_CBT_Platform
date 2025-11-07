"""
Image processing utilities for handling base64 images.
Used for server-side image operations like PDF generation, validation, etc.
"""

import base64
import io
from typing import Optional, Tuple
from PIL import Image


def decode_base64_image(base64_data: str) -> Optional[io.BytesIO]:
    """
    Decode base64 string to image bytes.
    
    Args:
        base64_data: Raw base64 string (without data URI prefix)
                    or full data URI (data:image/...;base64,...)
    
    Returns:
        BytesIO object containing decoded image bytes, or None if invalid
    
    Example:
        >>> img_io = decode_base64_image("iVBORw0KGgo...")
        >>> if img_io:
        >>>     img = Image.open(img_io)  # PIL Image
        >>>     # or for ReportLab:
        >>>     from reportlab.lib.utils import ImageReader
        >>>     img_reader = ImageReader(img_io)
    """
    if not base64_data:
        return None
    
    try:
        # Strip data URI prefix if present
        if base64_data.startswith('data:'):
            parts = base64_data.split(',', 1)
            if len(parts) == 2:
                base64_data = parts[1]
            else:
                return None
        
        # Remove whitespace
        base64_data = ''.join(base64_data.split())
        
        # Decode base64 to bytes
        img_bytes = base64.b64decode(base64_data)
        
        # Wrap in BytesIO (in-memory file-like object)
        return io.BytesIO(img_bytes)
    
    except Exception:
        return None


def validate_image(base64_data: str) -> Tuple[bool, Optional[str], Optional[Tuple[int, int]]]:
    """
    Validate base64 image and get its properties.
    
    Args:
        base64_data: Raw base64 string or full data URI
    
    Returns:
        Tuple of (is_valid, format, dimensions)
        - is_valid: True if image is valid
        - format: Image format (PNG, JPEG, GIF, etc.) or None
        - dimensions: (width, height) tuple or None
    
    Example:
        >>> valid, fmt, dims = validate_image("iVBORw0KGgo...")
        >>> if valid:
        >>>     print(f"Valid {fmt} image: {dims[0]}x{dims[1]} pixels")
    """
    img_io = decode_base64_image(base64_data)
    if not img_io:
        return False, None, None
    
    try:
        img = Image.open(img_io)
        return True, img.format, img.size
    except Exception:
        return False, None, None


def get_image_for_reportlab(base64_data: str):
    """
    Get ImageReader object for ReportLab PDF generation.
    
    Args:
        base64_data: Raw base64 string or full data URI
    
    Returns:
        ImageReader object or None if invalid
    
    Example:
        >>> from reportlab.lib.utils import ImageReader
        >>> img = get_image_for_reportlab(question.question_image)
        >>> if img:
        >>>     canvas.drawImage(img, x, y, width, height)
    """
    try:
        from reportlab.lib.utils import ImageReader
        
        img_io = decode_base64_image(base64_data)
        if not img_io:
            return None
        
        return ImageReader(img_io)
    except ImportError:
        # ReportLab not installed
        return None
    except Exception:
        return None


def compress_base64_image(base64_data: str, max_width: int = 800, quality: int = 85) -> Optional[str]:
    """
    Compress and resize base64 image to reduce size.
    
    Args:
        base64_data: Raw base64 string or full data URI
        max_width: Maximum width in pixels (maintains aspect ratio)
        quality: JPEG quality (1-100, higher = better quality)
    
    Returns:
        Compressed base64 string (raw, without data URI prefix) or None
    
    Example:
        >>> compressed = compress_base64_image(large_image, max_width=600, quality=80)
        >>> if compressed:
        >>>     question.question_image = compressed
        >>>     question.save()
    """
    img_io = decode_base64_image(base64_data)
    if not img_io:
        return None
    
    try:
        img = Image.open(img_io)
        
        # Convert RGBA to RGB if needed (for JPEG)
        if img.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        elif img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        # Resize if needed
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        
        # Save as JPEG to output buffer
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        # Encode back to base64
        compressed_bytes = output.read()
        return base64.b64encode(compressed_bytes).decode('utf-8')
    
    except Exception:
        return None


# Example usage in views or tasks
"""
# Example 1: PDF Generation
from neet_app.utils.image_utils import get_image_for_reportlab

def generate_test_pdf(test_session):
    canvas = Canvas(buffer)
    
    for answer in test_session.answers.all():
        question = answer.question
        
        # Add question image if present
        if question.question_image:
            img = get_image_for_reportlab(question.question_image)
            if img:
                canvas.drawImage(img, x=100, y=700, width=200, height=150)
    
    return buffer


# Example 2: Image Validation on Upload
from neet_app.utils.image_utils import validate_image

def validate_question_images(question_data):
    for field in ['question_image', 'option_a_image', ...]:
        if question_data.get(field):
            valid, fmt, dims = validate_image(question_data[field])
            if not valid:
                raise ValidationError(f"Invalid image in {field}")
            if dims[0] > 2000 or dims[1] > 2000:
                raise ValidationError(f"Image too large: {dims[0]}x{dims[1]}")


# Example 3: Compress Images Before Storing
from neet_app.utils.image_utils import compress_base64_image

def process_uploaded_questions(questions):
    for q in questions:
        if q.question_image:
            compressed = compress_base64_image(q.question_image, max_width=800, quality=85)
            if compressed:
                q.question_image = compressed
        q.save()
"""
