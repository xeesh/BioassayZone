import cv2
import numpy as np
import math
from typing import List, Dict, Any

class ImageProcessor:
    """Handles image processing operations for bioassay zone detection"""
    
    def __init__(self):
        self.dpi = 300  # Default DPI for pixel to mm conversion
        self.mm_per_inch = 25.4
    
    def detect_zones(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect circular inhibition zones in the image using OpenCV
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of detected zones with coordinates and measurements
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not load image")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            
            # Use HoughCircles to detect circular zones
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=30,
                param1=50,
                param2=30,
                minRadius=10,
                maxRadius=100
            )
            
            zones = []
            if circles is not None:
                circles = np.uint16(np.around(circles))
                
                for i, circle in enumerate(circles[0, :]):
                    x, y, radius = int(circle[0]), int(circle[1]), int(circle[2])
                    
                    # Convert pixel radius to mm diameter
                    diameter_mm = self.pixels_to_mm(radius * 2)
                    
                    zone = {
                        'id': f'auto_{i}',
                        'x': x,
                        'y': y,
                        'radius': radius,
                        'diameter_mm': round(diameter_mm, 2),
                        'type': 'automatic',
                        'confidence': self._calculate_confidence(gray, x, y, radius)
                    }
                    zones.append(zone)
            
            return zones
            
        except Exception as e:
            print(f"Zone detection error: {str(e)}")
            return []
    
    def pixels_to_mm(self, pixels: float) -> float:
        """Convert pixels to millimeters based on DPI"""
        inches = pixels / self.dpi
        mm = inches * self.mm_per_inch
        return mm
    
    def mm_to_pixels(self, mm: float) -> float:
        """Convert millimeters to pixels based on DPI"""
        inches = mm / self.mm_per_inch
        pixels = inches * self.dpi
        return pixels
    
    def _calculate_confidence(self, gray_image: np.ndarray, x: int, y: int, radius: int) -> float:
        """
        Calculate confidence score for detected zone based on edge strength
        
        Args:
            gray_image: Grayscale image
            x, y: Center coordinates
            radius: Radius of the zone
            
        Returns:
            Confidence score between 0 and 1
        """
        try:
            # Create a mask for the circular region
            mask = np.zeros(gray_image.shape, dtype=np.uint8)
            cv2.circle(mask, (x, y), radius, (255,), 2)
            
            # Apply Sobel edge detection
            sobelx = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
            edge_magnitude = np.sqrt(sobelx**2 + sobely**2)
            
            # Calculate average edge strength along the circle
            edge_values = edge_magnitude[mask == 255]
            if len(edge_values) > 0:
                confidence = np.mean(edge_values) / 255.0
                return min(1.0, float(confidence))
            else:
                return 0.0
                
        except Exception:
            return 0.5  # Default confidence
    
    def calculate_statistics(self, diameters: List[float]) -> Dict[str, float]:
        """
        Calculate basic statistics for zone diameters
        
        Args:
            diameters: List of diameter measurements in mm
            
        Returns:
            Dictionary containing statistical measures
        """
        if not diameters:
            return {}
        
        diameters_array = np.array(diameters, dtype=float)
        
        stats = {
            'count': len(diameters),
            'mean': float(np.mean(diameters_array)),
            'median': float(np.median(diameters_array)),
            'std_dev': float(np.std(diameters_array, ddof=1)) if len(diameters) > 1 else 0.0,
            'min': float(np.min(diameters_array)),
            'max': float(np.max(diameters_array)),
            'range': float(np.max(diameters_array) - np.min(diameters_array))
        }
        
        # Calculate coefficient of variation (CV%)
        if stats['mean'] > 0:
            stats['cv_percent'] = (stats['std_dev'] / stats['mean']) * 100
        else:
            stats['cv_percent'] = 0.0
        
        # Round to 3 decimal places
        for key, value in stats.items():
            if isinstance(value, float):
                stats[key] = round(value, 3)
        
        return stats
    
    def validate_zone(self, x: int, y: int, radius: int, image_shape: tuple) -> bool:
        """
        Validate that a zone is within image boundaries and reasonable size
        
        Args:
            x, y: Center coordinates
            radius: Radius of the zone
            image_shape: Shape of the image (height, width)
            
        Returns:
            True if zone is valid, False otherwise
        """
        height, width = image_shape[:2]
        
        # Check if center is within image
        if x < 0 or x >= width or y < 0 or y >= height:
            return False
        
        # Check if entire circle is within image
        if (x - radius < 0 or x + radius >= width or 
            y - radius < 0 or y + radius >= height):
            return False
        
        # Check reasonable size limits (5mm to 50mm diameter)
        diameter_mm = self.pixels_to_mm(radius * 2)
        if diameter_mm < 5 or diameter_mm > 50:
            return False
        
        return True
