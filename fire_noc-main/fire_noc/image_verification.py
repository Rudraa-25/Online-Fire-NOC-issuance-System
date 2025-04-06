import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from sklearn.cluster import KMeans
import os
from io import BytesIO
from PIL import Image

# Dictionary of equipment types with their respective features (for basic image classification)
EQUIPMENT_FEATURES = {
    'fire_extinguisher': {
        'color_range_lower': np.array([0, 100, 100]),  # Red HSV lower
        'color_range_upper': np.array([10, 255, 255]), # Red HSV upper
        'shape': 'cylindrical',
        'min_contour_area': 1000,
    },
    'fire_exit': {
        'color_range_lower': np.array([60, 100, 100]),  # Green HSV lower
        'color_range_upper': np.array([80, 255, 255]),  # Green HSV upper
        'shape': 'rectangular',
        'min_contour_area': 500,
    },
    'fire_safety_sign': {
        'color_range_lower': np.array([0, 0, 200]),    # White/bright HSV lower
        'color_range_upper': np.array([180, 30, 255]), # White/bright HSV upper
        'shape': 'rectangular',
        'min_contour_area': 300,
    },
    'water_infrastructure': {
        'color_range_lower': np.array([100, 100, 100]),  # Blue HSV lower
        'color_range_upper': np.array([140, 255, 255]),  # Blue HSV upper
        'shape': 'varied',
        'min_contour_area': 800,
    }
}

def pil_to_cv2(pil_image):
    """Convert PIL Image to OpenCV format (numpy array)"""
    # Convert PIL image to numpy array
    opencv_image = np.array(pil_image.convert('RGB'))
    # Convert RGB to BGR (OpenCV format)
    opencv_image = opencv_image[:, :, ::-1].copy()
    return opencv_image

def verify_equipment_type(image_file, equipment_type):
    """
    Verify if the image contains the specified fire safety equipment
    
    Args:
        image_file: Django uploaded file object
        equipment_type: String identifier of equipment (fire_extinguisher, fire_exit, etc.)
    
    Returns:
        tuple: (is_valid, confidence, message)
    """
    try:
        # Read image from uploaded file to PIL
        image = Image.open(image_file)
        # Convert PIL to OpenCV
        img = pil_to_cv2(image)
        
        # Convert to HSV for color detection
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Get features for this equipment type
        features = EQUIPMENT_FEATURES.get(equipment_type)
        if not features:
            return False, 0, "Unknown equipment type"
        
        # Create mask based on color range for this equipment
        mask = cv2.inRange(hsv, features['color_range_lower'], features['color_range_upper'])
        
        # Find contours in the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours based on area
        valid_contours = [c for c in contours if cv2.contourArea(c) > features['min_contour_area']]
        
        if not valid_contours:
            return False, 0, f"No {equipment_type.replace('_', ' ')} detected in the image"
        
        # Calculate confidence based on contour area and count
        total_area = sum(cv2.contourArea(c) for c in valid_contours)
        img_area = img.shape[0] * img.shape[1]
        confidence = min(100, (total_area / img_area) * 100 * len(valid_contours))
        
        # Simple shape analysis
        if features['shape'] == 'cylindrical':
            # For cylinders (e.g., fire extinguishers), check aspect ratio
            for c in valid_contours:
                x, y, w, h = cv2.boundingRect(c)
                aspect_ratio = float(h)/w
                if 1.5 <= aspect_ratio <= 5.0:  # Typical aspect ratio for extinguishers
                    return True, confidence, f"Valid {equipment_type.replace('_', ' ')} detected"
        
        elif features['shape'] == 'rectangular':
            # For rectangular items (e.g., exit signs), check rectangularity
            for c in valid_contours:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.04 * peri, True)
                if len(approx) == 4:  # Rectangle has 4 corners
                    return True, confidence, f"Valid {equipment_type.replace('_', ' ')} detected"
        
        # For varied shapes or if specific shape check failed but got valid contours
        if len(valid_contours) > 0:
            return True, confidence * 0.7, f"Possible {equipment_type.replace('_', ' ')} detected"
            
        return False, 0, f"Image does not appear to contain a {equipment_type.replace('_', ' ')}"
    
    except Exception as e:
        return False, 0, f"Error analyzing image: {str(e)}"

def is_duplicate_image(new_image, existing_images, threshold=0.85):
    """
    Check if an image is a duplicate of any existing images
    
    Args:
        new_image: Django uploaded file object
        existing_images: List of Django uploaded file objects
        threshold: Similarity threshold (0.0-1.0, higher means more similar)
    
    Returns:
        tuple: (is_duplicate, duplicate_index, similarity_score)
    """
    try:
        # Open the new image
        new_img = Image.open(new_image)
        new_img_cv = pil_to_cv2(new_img)
        
        # Resize for consistency
        new_img_cv = cv2.resize(new_img_cv, (200, 200))
        new_img_gray = cv2.cvtColor(new_img_cv, cv2.COLOR_BGR2GRAY)
        
        for i, existing_image in enumerate(existing_images):
            # Open existing image
            existing_img = Image.open(existing_image)
            existing_img_cv = pil_to_cv2(existing_img)
            
            # Resize for consistency
            existing_img_cv = cv2.resize(existing_img_cv, (200, 200))
            existing_img_gray = cv2.cvtColor(existing_img_cv, cv2.COLOR_BGR2GRAY)
            
            # Calculate similarity using SSIM
            score, _ = ssim(new_img_gray, existing_img_gray, full=True)
            
            if score > threshold:
                return True, i, score
                
        return False, None, 0.0
    
    except Exception as e:
        return False, None, f"Error checking for duplicates: {str(e)}"

def extract_image_features(image_file):
    """
    Extract basic features from an image for classification
    
    Args:
        image_file: Django uploaded file object
    
    Returns:
        dict: Features extracted from the image
    """
    try:
        # Open image
        image = Image.open(image_file)
        img = pil_to_cv2(image)
        
        # Resize for consistency
        img = cv2.resize(img, (200, 200))
        
        # Convert to HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Calculate dominant colors using KMeans
        pixels = hsv.reshape(-1, 3)
        kmeans = KMeans(n_clusters=3, n_init=10)
        kmeans.fit(pixels)
        dominant_colors = kmeans.cluster_centers_
        
        # Calculate histogram for texture analysis
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 30], [0, 180, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        
        return {
            'dominant_colors': dominant_colors,
            'histogram': hist,
            'width': img.shape[1],
            'height': img.shape[0],
        }
        
    except Exception as e:
        return {'error': str(e)} 