import os
from langchain_google_genai import GoogleGenerativeAI
import logging
import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import google.generativeai as genai
import time
from functools import wraps

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_count = 0
            wait_time = backoff_in_seconds
            
            while retry_count < retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if "429" in str(e) and retry_count < retries - 1:
                        logger.warning(f"API quota exceeded, retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        retry_count += 1
                        wait_time *= 2  # Exponential backoff
                        continue
                    raise
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fashion_recommendations.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FashionRecommender:
    """Main class for fashion recommendations"""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found")
        self.configure_api()
        
    def configure_api(self):
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.api_manager = GoogleGenerativeAI(model="gemini-pro", api_key=self.api_key)
        
    @retry_with_backoff()
    async def get_outfit_recommendations(self, gender, topwear_size, bottomwear_size, 
                                      skin_tone, occasion, foot_size, image_path=None, 
                                      additional_info="", custom_occasion=""):
        """Get outfit recommendations based on user preferences"""
        try:
            # Handle custom occasion if user selected "other"
            actual_occasion = custom_occasion if occasion.lower() == "other" and custom_occasion else occasion
            
            # Create prompt for the AI
            prompt = f"""
            Generate fashion recommendations for:
            Gender: {gender}
            Topwear Size: {topwear_size}
            Bottomwear Size: {bottomwear_size}
            Skin Tone: {skin_tone}
            Occasion: {actual_occasion}
            Foot Size: {foot_size}
            Additional Information: {additional_info}

            Provide specific recommendations with explanations for:
            1. Topwear (with explanation of why it's suitable)
            2. Bottomwear (with explanation of why it's suitable)
            3. Footwear (with explanation of why it's suitable)
            4. Accessories (with explanation of why they complement the outfit)
            5. Color combinations (with explanation of why they work well)
            6. Styling tips (with explanation of the benefits)

            Format the response as a structured JSON with the following structure:
            {{
                "topwear": [
                    {{"item": "Item description", "explanation": "Why it's suitable"}}
                ],
                "bottomwear": [
                    {{"item": "Item description", "explanation": "Why it's suitable"}}
                ],
                "footwear": [
                    {{"item": "Item description", "explanation": "Why it's suitable"}}
                ],
                "accessories": [
                    {{"item": "Item description", "explanation": "Why they complement the outfit"}}
                ],
                "color_combinations": [
                    {{"item": "Color combination description", "explanation": "Why they work well"}}
                ],
                "styling_tips": [
                    {{"item": "Styling tip", "explanation": "Benefits of this tip"}}
                ]
            }}
            
            Ensure that all sections are included in the response, especially the color_combinations section.
            """
            
            # Use the AI model to generate recommendations
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Extract JSON from the response if needed
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content
            
            try:
                recommendations = json.loads(json_str)
                
                # Ensure all required sections exist
                required_sections = ['topwear', 'bottomwear', 'footwear', 'accessories', 'color_combinations', 'styling_tips']
                for section in required_sections:
                    if section not in recommendations:
                        recommendations[section] = []
                
                # For backward compatibility, also add 'colors' if 'color_combinations' exists
                if 'color_combinations' in recommendations and 'colors' not in recommendations:
                    recommendations['colors'] = recommendations['color_combinations']
                
                return recommendations
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON: {str(e)}")
                logger.error(f"JSON string: {json_str}")
                raise
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            raise

    @retry_with_backoff()
    async def extract_image_metadata(self, image_path: str) -> dict:
        """Extract metadata from uploaded image"""

        try:
            # Use AI to extract relevant fashion metadata from the image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            prompt = """
            Analyze this image and extract fashion-relevant metadata.
            Identify:
            1. Dominant colors
            2. Clothing types visible
            3. Style category (casual, formal, etc.)
            4. Season appropriateness
            5. Any distinctive patterns or textures
            
            Format the response as JSON.
            """
            
            response = self.model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_data}])
            content = response.text
            
            # Extract JSON from the response
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content
                
            try:
                metadata = json.loads(json_str)
                # Add basic file metadata
                metadata['format'] = image_path.split('.')[-1]
                metadata['timestamp'] = datetime.now().isoformat()
                return metadata
            except json.JSONDecodeError:
                # If JSON parsing fails, return basic metadata
                return {
                    'format': image_path.split('.')[-1],
                    'timestamp': datetime.now().isoformat(),
                    'analysis_status': 'failed'
                }
                
        except Exception as e:
            logger.error(f"Error extracting image metadata: {str(e)}")
            return {
                'format': image_path.split('.')[-1] if image_path else 'unknown',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
            
    @retry_with_backoff()
    async def detect_clothing_items(self, image_path: str) -> list:
        """Detect clothing items in the image using AI"""
        try:
            # Use AI to detect clothing items in the image
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            prompt = """
            Analyze this image and identify all clothing items visible.
            For each item, provide:
            1. Type of clothing (e.g., shirt, pants, dress)
            2. Color
            3. Style details
            4. Material (if identifiable)
            
            Format the response as a JSON array of objects.
            """
            
            response = self.model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_data}])
            content = response.text
            
            # Extract JSON from the response
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content
                
            try:
                clothing_items = json.loads(json_str)
                return clothing_items if isinstance(clothing_items, list) else []
            except json.JSONDecodeError:
                return []
                
        except Exception as e:
            logger.error(f"Error detecting clothing items: {str(e)}")
            return []

    @retry_with_backoff()
    async def get_traditional_recommendations(self, context: dict) -> dict:
        """Get recommendations for traditional/cultural attire"""
        try:
            cultural_context = context.get('cultural_context', '')
            event_type = context.get('event_type', '')
            gender = context.get('gender', '')
            additional_info = context.get('additional_info', '')
            
            # Create prompt for the AI
            prompt = f"""
            Generate detailed traditional fashion recommendations for:
            Cultural Context: {cultural_context}
            Event Type: {event_type}
            Gender: {gender}
            Additional Information: {additional_info}

            For each recommendation, provide:
            1. The name of the traditional garment
            2. A brief description of its cultural significance
            3. How it should be worn
            4. Appropriate accessories to pair with it
            5. Color recommendations based on the specific cultural context
            
            Format the response as a structured JSON with the following categories:
            - main_garments (array of objects with name, description, cultural_significance)
            - accessories (array of objects with name, description, cultural_significance)
            - color_recommendations (array of objects with color, significance)
            - styling_tips (array of strings)
            - cultural_etiquette (array of strings)
            """
            
            # Use the AI model to generate recommendations
            response = self.model.generate_content(prompt)
            content = response.text
            
            # Extract JSON from the response if needed
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content
            
            try:
                recommendations = json.loads(json_str)
                return recommendations
            except Exception as json_error:
                logger.error(f"Error processing AI response: {str(json_error)}")
                # Fall back to a basic structure
                return {
                    'main_garments': [],
                    'accessories': [],
                    'color_recommendations': [],
                    'styling_tips': [],
                    'cultural_etiquette': []
                }
            
        except Exception as e:
            logger.error(f"Error generating traditional recommendations: {str(e)}")
            raise

    @retry_with_backoff()
    async def detect_skin_tone(self, image_path: str) -> str:
        """Detect skin tone from image"""
        try:
            # Use AI to analyze the image and detect skin tone
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            prompt = "Analyze this image and determine the skin tone of the person. Describe it as one of: fair, light, medium, olive, tan, deep, or dark."
            
            response = self.model.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_data}])
            content = response.text.lower()
            
            # Extract the skin tone from the response
            skin_tones = ["fair", "light", "medium", "olive", "tan", "deep", "dark"]
            detected_tone = "medium"  # Default
            
            for tone in skin_tones:
                if tone in content:
                    detected_tone = tone
                    break
                    
            logger.info(f"Detected skin tone: {detected_tone}")
            return detected_tone
            
        except Exception as e:
            logger.error(f"Error detecting skin tone: {str(e)}")
            return "medium"  # Default fallback