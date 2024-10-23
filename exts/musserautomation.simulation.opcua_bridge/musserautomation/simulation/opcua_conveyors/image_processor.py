import cv2
import numpy as np
import os
from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file, get_viewport_from_window_name

class ImageProcessor:
    def __init__(self):
        # You can initialize any settings you want here, such as thresholds, etc.
        pass

    def capture_image(self):
        try:
            vp_api = get_viewport_from_window_name("Viewport 2")
            capture_viewport_to_file(vp_api, r"D:\Projects\MusserAutomation\omniverse-things\opencv-processing\data\screenshot.png")
        except: 
            vp_api = get_active_viewport()
            capture_viewport_to_file(vp_api, r"D:\Projects\MusserAutomation\omniverse-things\opencv-processing\data\screenshot.png")

    def process_image(self):
        """
        Process the image to find a case, draw a bounding box, 
        and return centroid coordinates and orientation.
        
        :param image: input image from the vision system
        :return: (x_centroid, y_centroid, orientation_angle), processed_image
        """
        image = cv2.imread(r"D:\Projects\MusserAutomation\omniverse-things\opencv-processing\data\screenshot.png")

        # Convert image to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Threshold the image to create a binary image
        _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
        
        # Find contours in the thresholded image
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None, image  # No contours found
        
        # Assume the largest contour is the case (you can adjust the selection logic as needed)
        case_contour = max(contours, key=cv2.contourArea)
        
        # Get the bounding box for the case
        rect = cv2.minAreaRect(case_contour)
        box = cv2.boxPoints(rect)
        box = np.int32(box)

        # Draw the bounding box in green
        cv2.drawContours(image, [box], 0, (0, 255, 0), 2)

        # Get the centroid of the contour (case)
        M = cv2.moments(case_contour)
        if M["m00"] != 0:
            x_centroid = int(M["m10"] / M["m00"])
            y_centroid = int(M["m01"] / M["m00"])
        else:
            x_centroid, y_centroid = 0, 0
        
        # Get the orientation angle of the case
        orientation_angle = rect[2]  # This is the angle of the rotated bounding box

        # Add the coordinates and orientation as text on the image
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = f"({x_centroid}mm, {y_centroid}mm, {orientation_angle:.2f} deg)"
        text_position = (x_centroid - 400, y_centroid + 200)  # Position it near the centroid

        # Overlay the text onto the image
        cv2.putText(image, text, text_position, font, 2.0, (0, 255, 0), 2, cv2.LINE_AA)

        # Assuming 'image_path' is the path of the original image passed to the method
        output_path = "D:\Projects\MusserAutomation\omniverse-things\opencv-processing\data\processed.png"

        # Save the processed image with the overlay
        cv2.imwrite(output_path, image)
        
        # Return the centroid, orientation, and the image with drawn bounding box
        return (x_centroid, y_centroid, orientation_angle), image