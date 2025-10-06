#!/usr/bin/env python3
"""
Tipitaka Image Processing Utility

This script processes images in /public/tipitaka directory:
1. Crops 5mm margins from alHey Cortana, call me time now is it uploading? l sides
2. Resizes all images to match the first image dimensions  
3. Applies deskew correction
4. Overwrites original files

Author: AI Assistant
Date: 2025-10-05
"""

import os
import sys
import subprocess
import math
from pathlib import Path
from PIL import Image, ImageFile
import numpy as np
from typing import List, Tuple, Optional

# Enable loading of truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

# Fixed crop margin
CROP_MARGIN_MM = 5.0

def activate_venv():
    """Activate virtual environment"""
    venv_script = Path(__file__).parent.parent.parent / "venv.ps1"
    if venv_script.exists():
        print("🔧 Activating virtual environment...")
        try:
            # Run PowerShell to activate venv
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(venv_script)], 
                capture_output=True, text=True, check=True
            )
            print("✅ Virtual environment activated")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Could not activate virtual environment: {e}")
    else:
        print("⚠️  Warning: venv.ps1 not found")

def install_requirements():
    """Install required packages"""
    required_packages = ['Pillow', 'numpy<2.0', 'deskew', 'scikit-image', 'opencv-python']
    
    print("📦 Checking required packages...")
    for package in required_packages:
        package_name = package.split('<')[0].split('>')[0].split('=')[0]  # Extract base name
        try:
            if package_name == 'scikit-image':
                import skimage
            elif package_name == 'Pillow':
                from PIL import Image
            elif package_name == 'opencv-python':
                import cv2
            else:
                __import__(package_name.lower().replace('-', '_'))
            print(f"✅ {package_name} - installed")
        except ImportError:
            print(f"⬇️  Installing {package}...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✅ {package} - installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {package}: {e}")
                return False
    return True

def mm_to_pixels(mm: float, dpi: int = 300) -> int:
    """
    Convert millimeters to pixels based on DPI.
    
    Args:
        mm: Distance in millimeters
        dpi: Dots per inch (default: 300)
    
    Returns:
        Equivalent pixels
    """
    inches = mm / 25.4  # 1 inch = 25.4 mm
    return int(inches * dpi)

def get_image_dpi(image: Image.Image) -> Tuple[int, int]:
    """
    Get DPI from image metadata, with fallback to 300 DPI.
    
    Args:
        image: PIL Image object
    
    Returns:
        Tuple of (horizontal_dpi, vertical_dpi)
    """
    dpi = image.info.get('dpi', (300, 300))
    if isinstance(dpi, (int, float)):
        dpi = (dpi, dpi)
    return dpi

def deskew_image_opencv(image_path: Path) -> bool:
    """
    Apply deskew correction using OpenCV and deskew library.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        import cv2
        from deskew import determine_skew
        from skimage import io
        from skimage.color import rgb2gray
        
        # Read image
        image = io.imread(str(image_path))
        
        # Ensure image is in correct format for OpenCV
        if image.dtype != np.uint8:
            if image.dtype == bool:
                image = image.astype(np.uint8) * 255
            elif image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
            else:
                image = image.astype(np.uint8)
        
        # Convert to grayscale for skew detection
        if len(image.shape) == 3:
            grayscale = rgb2gray(image)
        else:
            grayscale = image
        
        # Determine skew angle with multiple methods for validation
        angle = determine_skew(grayscale, num_peaks=50)  # Increase peaks for better accuracy
        
        if angle is None:
            print(f"    ✅ No skew detected, image is straight")
            return True
        
        # Safety check: reject extreme angles (likely false detection)
        if abs(angle) > 5.0:
            print(f"    ⚠️  Extreme angle detected ({angle:.2f}°), likely false positive - skipping deskew")
            return True
        
        # Conservative threshold: only deskew significant angles
        if abs(angle) < 1.0:
            print(f"    ✅ Skew angle minimal ({angle:.2f}°), skipping")
            return True
        
        # Additional validation: try with different parameters
        angle2 = determine_skew(grayscale, num_peaks=20, angle_pm_90=True)
        if angle2 is not None and abs(angle - angle2) > 5.0:
            print(f"    ⚠️  Inconsistent angle detection ({angle:.2f}° vs {angle2:.2f}°), skipping for safety")
            return True
        
        print(f"    🔄 Deskewing by {angle:.2f}° - {image_path.parent.name}/{image_path.name}")
        
        # Rotate image using OpenCV
        def rotate_opencv(img: np.ndarray, angle: float, background=(255, 255, 255)) -> np.ndarray:
            if len(img.shape) == 2:
                old_height, old_width = img.shape
            else:
                old_height, old_width = img.shape[:2]
            
            angle_radian = math.radians(angle)
            width = abs(np.sin(angle_radian) * old_height) + abs(np.cos(angle_radian) * old_width)
            height = abs(np.sin(angle_radian) * old_width) + abs(np.cos(angle_radian) * old_height)
            
            image_center = (old_width / 2, old_height / 2)
            rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
            rot_mat[1, 2] += (width - old_width) / 2
            rot_mat[0, 2] += (height - old_height) / 2
            
            if len(img.shape) == 3:
                borderValue = background
            else:
                borderValue = background[0] if isinstance(background, tuple) else background
            
            return cv2.warpAffine(img, rot_mat, (int(round(width)), int(round(height))), 
                                borderValue=borderValue)
        
        # Create backup of original before rotation
        backup_path = image_path.with_suffix('.backup' + image_path.suffix)
        import shutil
        shutil.copy2(image_path, backup_path)
        
        # Rotate the image
        rotated = rotate_opencv(image, angle, (255, 255, 255))
        
        # Validate rotation result
        if rotated is None or rotated.size == 0:
            print(f"    ⚠️  Rotation failed, restoring backup")
            shutil.copy2(backup_path, image_path)
            backup_path.unlink()  # Remove backup
            return False
        
        # Save rotated image
        io.imsave(str(image_path), rotated.astype(np.uint8))
        
        # Remove backup if successful
        backup_path.unlink()
        
        print(f"    ✅ Deskewed successfully")
        return True
        
    except ImportError as e:
        print(f"    ⚠️  Missing package: {e}")
        return False
    except Exception as e:
        print(f"    ⚠️  Deskew failed: {e}")
        return False

def deskew_image_pil(image_path: Path) -> bool:
    """
    Fallback deskew method using PIL rotation.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from deskew import determine_skew
        
        # Load image with PIL
        with Image.open(image_path) as img:
            # Convert to numpy for skew detection
            img_array = np.array(img)
            
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                from skimage.color import rgb2gray
                grayscale = rgb2gray(img_array)
            else:
                grayscale = img_array
            
        # Determine skew angle with safety checks
        angle = determine_skew(grayscale, num_peaks=50)
        
        if angle is None:
            print(f"    ✅ No skew detected (PIL fallback)")
            return True
        
        # Safety check: reject extreme angles
        if abs(angle) > 5.0:
            print(f"    ⚠️  Extreme angle detected ({angle:.2f}°), skipping (PIL fallback)")
            return True
        
        # Conservative threshold
        if abs(angle) < 1.0:
            print(f"    ✅ Skew angle minimal ({angle:.2f}°), skipping (PIL)")
            return True
        
        print(f"    🔄 Deskewing by {angle:.2f}° (PIL fallback) - {image_path.parent.name}/{image_path.name}")        # Create backup before rotation
        backup_path = image_path.with_suffix('.backup' + image_path.suffix)
        import shutil
        shutil.copy2(image_path, backup_path)
        
        # Rotate image with PIL
        rotated = img.rotate(-angle, expand=True, fillcolor='white')
        
        # Validate rotation result
        if rotated.size[0] == 0 or rotated.size[1] == 0:
            print(f"    ⚠️  PIL rotation failed, restoring backup")
            shutil.copy2(backup_path, image_path)
            backup_path.unlink()
            return False
        
        # Save rotated image
        rotated.save(image_path, quality=95, optimize=True)
        
        # Remove backup if successful
        backup_path.unlink()
        
        print(f"    ✅ Deskewed successfully (PIL)")
        return True
            
    except ImportError as e:
        print(f"    ⚠️  Missing package for fallback: {e}")
        return False
    except Exception as e:
        print(f"    ⚠️  Fallback deskew failed: {e}")
        return False

def process_image(image_path: Path, target_size: Optional[Tuple[int, int]] = None) -> Tuple[bool, Optional[Tuple[int, int]]]:
    """
    Process a single image: crop, resize, and deskew.
    
    Args:
        image_path: Path to the input image
        target_size: Target size (width, height) to resize to, if None will crop only
    
    Returns:
        Tuple of (success, final_size)
    """
    try:
        with Image.open(image_path) as img:
            # Get image DPI
            dpi_x, dpi_y = get_image_dpi(img)
            
            # Convert mm to pixels
            crop_pixels_x = mm_to_pixels(CROP_MARGIN_MM, dpi_x)
            crop_pixels_y = mm_to_pixels(CROP_MARGIN_MM, dpi_y)
            
            # Get current dimensions
            width, height = img.size
            
            # Calculate crop box (left, top, right, bottom)
            left = crop_pixels_x
            top = crop_pixels_y
            right = width - crop_pixels_x
            bottom = height - crop_pixels_y
            
            # Validate crop dimensions
            if left >= right or top >= bottom:
                print(f"    ⚠️  Crop margin too large, skipping crop")
                cropped_img = img.copy()
                final_size = (width, height)
            else:
                # Crop the image
                cropped_img = img.crop((left, top, right, bottom))
                final_size = (right - left, bottom - top)
                print(f"    ✂️  Cropped from {width}×{height} to {final_size[0]}×{final_size[1]}")
            
            # Resize to target size if specified
            if target_size:
                cropped_img = cropped_img.resize(target_size, Image.Resampling.LANCZOS)
                final_size = target_size
                print(f"    📏 Resized to {target_size[0]}×{target_size[1]}")
            
            # Save the processed image
            cropped_img.save(image_path, quality=95, optimize=True)
        
        # Apply deskew - try OpenCV first, fallback to PIL
        deskew_success = deskew_image_opencv(image_path)
        if not deskew_success:
            print(f"    🔄 Trying PIL fallback...")
            deskew_success = deskew_image_pil(image_path)
        
        if not deskew_success:
            print(f"    ⚠️  Deskew failed with both methods, continuing without deskew")
        
        return True, final_size
        
    except Exception as e:
        print(f"    ❌ Error: {str(e)}")
        return False, None

def find_images(directory: Path) -> List[Path]:
    """
    Recursively find all supported image files in a directory.
    
    Args:
        directory: Directory to search
    
    Returns:
        List of image file paths sorted by name with 1.png first
    """
    image_files = []
    
    for file_path in directory.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FORMATS:
            image_files.append(file_path)
    
    # Custom sort function for proper numerical order by folder then by file number
    def sort_key(path: Path) -> tuple:
        name = path.stem  # filename without extension
        parent_name = path.parent.name
        
        # Extract folder number for proper folder ordering
        try:
            # Try to extract number from folder name (e.g., "1", "2", "10", "ch1", etc.)
            import re
            folder_num_match = re.search(r'\d+', parent_name)
            if folder_num_match:
                folder_num = int(folder_num_match.group())
            else:
                folder_num = 999999  # Put non-numeric folders at the end
        except:
            folder_num = 999999
        
        # Extract file number for proper file ordering
        try:
            # Handle pure numbers or mixed strings like "1", "01", "001", etc.
            file_num = int(name)
        except ValueError:
            # If not a pure number, extract the first number found
            import re
            num_match = re.search(r'\d+', name)
            if num_match:
                file_num = int(num_match.group())
            else:
                file_num = 999999  # Put non-numeric files at the end
        
        # Return tuple for sorting: (folder_number, file_number, folder_name, file_name)
        # This ensures numerical order within each folder and proper folder order
        return (folder_num, file_num, parent_name, name)
    
    return sorted(image_files, key=sort_key)

def find_first_image(directory: Path) -> Optional[Path]:
    """
    Find the first image file named '1.png' or similar.
    
    Args:
        directory: Directory to search
    
    Returns:
        Path to the first image or None
    """
    # Look for common first file patterns
    first_patterns = ['1.png', '1.jpg', '1.jpeg', '01.png', '01.jpg', '001.png']
    
    for pattern in first_patterns:
        for file_path in directory.rglob(pattern):
            if file_path.is_file():
                return file_path
    
    # If no specific pattern found, return the first image alphabetically
    images = find_images(directory)
    return images[0] if images else None

def main():
    """Main function"""
    print("=" * 70)
    print("🏛️  Tipitaka Image Processing Utility")
    print("=" * 70)
    
    # Activate virtual environment (informational only - assumes already activated)
    print("🔧 Ensuring virtual environment is active...")
    
    # Install required packages
    if not install_requirements():
        print("❌ Failed to install required packages")
        sys.exit(1)
    
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    tipitaka_dir = project_root / "public" / "tipitaka"
    
    print(f"\n📁 Target directory: {tipitaka_dir}")
    
    if not tipitaka_dir.exists():
        print(f"❌ Directory not found: {tipitaka_dir}")
        sys.exit(1)
    
    # Find all images
    print(f"\n🔍 Scanning for images...")
    image_files = find_images(tipitaka_dir)
    
    if not image_files:
        print("❌ No image files found")
        return
    
    print(f"📊 Found {len(image_files)} image files")
    
    # Find the first image (1.png or similar)
    first_image = find_first_image(tipitaka_dir)
    
    if not first_image:
        print("❌ No reference image found (looking for 1.png or similar)")
        # If no 1.png found, use the first image from sorted list
        first_image = image_files[0] if image_files else None
        if not first_image:
            return
        print(f"📐 Using first available image as reference: {first_image.name}")
    else:
        relative_path = first_image.relative_to(tipitaka_dir)
        folder_name = relative_path.parent.name if relative_path.parent.name != '.' else 'root'
        print(f"📐 Reference image: 📁{folder_name}/{first_image.name}")
    
    # Show summary and confirm
    print(f"\n📋 Processing summary:")
    print(f"   • Crop margin: {CROP_MARGIN_MM}mm from each side")
    print(f"   • Resize all to match: {first_image.name}")
    print(f"   • Apply deskew correction")
    print(f"   • Overwrite original files")
    print(f"   • Total files: {len(image_files)}")
    
    confirm = input(f"\n❓ Proceed with processing? (y/n) [y]: ").strip().lower()
    if confirm in ['n', 'no', 'ไม่']:
        print("❌ Operation cancelled")
        return
    
    # Process the first image to get target dimensions
    print(f"\n🚀 Processing reference image...")
    relative_path = first_image.relative_to(tipitaka_dir)
    folder_name = relative_path.parent.name if relative_path.parent.name != '.' else 'root'
    print(f"[REF] 📁{folder_name}/{first_image.name}")
    success, target_size = process_image(first_image)
    
    if not success or not target_size:
        print("❌ Failed to process reference image")
        return
    
    print(f"✅ Reference processed → {target_size[0]}×{target_size[1]} pixels")
    
    # Process remaining images
    print(f"\n🔄 Processing remaining images...")
    print("-" * 70)
    
    success_count = 1  # Reference image already processed
    remaining_images = [img for img in image_files if img != first_image]
    
    for i, image_file in enumerate(remaining_images, 1):
        # Get relative path for display
        relative_path = image_file.relative_to(tipitaka_dir)
        folder_name = relative_path.parent.name if relative_path.parent.name != '.' else 'root'
        print(f"[{i+1}/{len(image_files)}] 📁{folder_name}/{image_file.name}")
        
        success, _ = process_image(image_file, target_size)
        if success:
            success_count += 1
            print(f"    ✅ Processed → {target_size[0]}×{target_size[1]} pixels")
        else:
            print(f"    ❌ Failed")
    
    # Summary
    print("-" * 70)
    print(f"📊 Processing complete!")
    print(f"   ✅ Successful: {success_count}/{len(image_files)} files")
    print(f"   📐 Final size: {target_size[0]}×{target_size[1]} pixels")
    print(f"   📁 Location: {tipitaka_dir}")
    
    if success_count == len(image_files):
        print("\n🎉 All images processed successfully!")
    else:
        failed_count = len(image_files) - success_count
        print(f"\n⚠️  {failed_count} images failed to process")
    
    print("\n✨ Processing complete!")

if __name__ == "__main__":
    main()