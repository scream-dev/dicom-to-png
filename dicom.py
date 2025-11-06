import os
import png
import pydicom
import argparse
import numpy as np
import logging
from pathlib import Path

def mri_to_png(mri_file, png_file):
    """Function to convert from a DICOM image to png

    @param mri_file: An opened file like object to read the dicom data
    @param png_file: An opened file like object to write the png data
    """
    try:
        # Read DICOM file using pydicom
        plan = pydicom.dcmread(mri_file)
        
        # Check if pixel array exists
        if not hasattr(plan, 'pixel_array'):
            raise ValueError("DICOM file does not contain image data")
        
        # Get pixel array
        pixel_array = plan.pixel_array
        
        # Handle different data types
        if pixel_array.dtype == np.uint16:
            # For 16-bit images, scale to 8-bit
            if pixel_array.max() > 0:
                image_2d_scaled = ((pixel_array.astype(float) / pixel_array.max()) * 255).astype(np.uint8)
            else:
                image_2d_scaled = pixel_array.astype(np.uint8)
        elif pixel_array.dtype == np.uint8:
            # Already 8-bit
            image_2d_scaled = pixel_array
        else:
            # For other types, normalize to 0-255
            if pixel_array.max() > pixel_array.min():
                image_2d_scaled = ((pixel_array.astype(float) - pixel_array.min()) / 
                                 (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
            else:
                image_2d_scaled = pixel_array.astype(np.uint8)
        
        # Get dimensions (width, height)
        height, width = pixel_array.shape
        
        # Write PNG file
        w = png.Writer(width, height, greyscale=True)
        w.write(png_file, image_2d_scaled.tolist())
        
    except Exception as e:
        raise RuntimeError(f"Error converting DICOM to PNG: {str(e)}")

def convert_file(mri_file_path, png_file_path):
    """Function to convert an MRI binary file to a PNG image file.

    @param mri_file_path: Full path to the mri file
    @param png_file_path: Full path to the generated png file
    """
    # Making sure that the mri file exists
    if not os.path.exists(mri_file_path):
        raise FileNotFoundError(f'File "{mri_file_path}" does not exist')

    # Making sure the png file does not exist
    if os.path.exists(png_file_path):
        raise FileExistsError(f'File "{png_file_path}" already exists')

    # Create directory for output file if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(png_file_path)), exist_ok=True)

    try:
        with open(mri_file_path, 'rb') as mri_file:
            with open(png_file_path, 'wb') as png_file:
                mri_to_png(mri_file, png_file)
    except Exception as e:
        # Clean up partially created file on error
        if os.path.exists(png_file_path):
            os.remove(png_file_path)
        raise e

def convert_folder(mri_folder, png_folder):
    """Convert all MRI files in a folder to png files in a destination folder"""
    
    # Create the main output folder
    os.makedirs(png_folder, exist_ok=True)

    # Counters for statistics
    success_count = 0
    fail_count = 0

    # Recursively traverse all sub-folders in the path
    for root, dirs, files in os.walk(mri_folder):
        for file in files:
            mri_file_path = os.path.join(root, file)
            
            # Only process files (not directories)
            if os.path.isfile(mri_file_path):
                try:
                    # Check if it's a DICOM file by extension or try to read it
                    if not (file.lower().endswith(('.dcm', '.dicom')) or 
                           pydicom.misc.is_dicom(mri_file_path)):
                        continue
                    
                    # Replicate the original file structure
                    rel_path = os.path.relpath(root, mri_folder)
                    png_folder_path = os.path.join(png_folder, rel_path)
                    os.makedirs(png_folder_path, exist_ok=True)
                    
                    # Create output filename
                    png_filename = os.path.splitext(file)[0] + '.png'
                    png_file_path = os.path.join(png_folder_path, png_filename)

                    # Convert the file
                    convert_file(mri_file_path, png_file_path)
                    print(f'SUCCESS: {mri_file_path} -> {png_file_path}')
                    success_count += 1
                    
                except pydicom.errors.InvalidDicomError:
                    print(f'SKIP: {mri_file_path} - Not a valid DICOM file')
                except Exception as e:
                    print(f'FAIL: {mri_file_path} -> {png_file_path} : {e}')
                    fail_count += 1

    print(f"\nConversion completed: {success_count} successful, {fail_count} failed")

def main():
    """Main function with proper argument handling"""
    parser = argparse.ArgumentParser(description="Convert a DICOM MRI file to PNG")
    parser.add_argument('-f', '--folder', action='store_true',
                       help='Convert entire folder recursively')
    parser.add_argument('dicom_path', help='Full path to the DICOM file or folder')
    parser.add_argument('png_path', help='Full path to the output PNG file or folder')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    
    try:
        if args.folder:
            if not os.path.isdir(args.dicom_path):
                logger.error(f"Source path is not a directory: {args.dicom_path}")
                return 1
                
            logger.info(f"Converting folder: {args.dicom_path} -> {args.png_path}")
            convert_folder(args.dicom_path, args.png_path)
        else:
            if not os.path.isfile(args.dicom_path):
                logger.error(f"Source file does not exist: {args.dicom_path}")
                return 1
                
            logger.info(f"Converting file: {args.dicom_path} -> {args.png_path}")
            convert_file(args.dicom_path, args.png_path)
            logger.info("Conversion completed successfully")
            
        return 0
        
    except KeyboardInterrupt:
        logger.info("Conversion interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        return 1

if __name__ == '__main__':
    exit(main())
