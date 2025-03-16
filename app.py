# Remove duplicate imports
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, session
import os
import uuid
import asyncio
from datetime import datetime
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
from langchain_google_genai import GoogleGenerativeAI

# Set API key in environment variables before importing framework
API_KEY = "AIzaSyBBb4uTjhZzjKNa7vaJm2MJZoeOPBblX24"
os.environ["GEMINI_API_KEY"] = API_KEY

# Now import framework and initialize recommender
from framework import FashionRecommender
recommender = FashionRecommender(API_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
logger.addHandler(handler)

# Create an instance of the Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/images/uploads')

# Cache for recommendations
recommendation_cache = {}

# Constants
VALID_GENDERS = {'male', 'female', 'non-binary', 'transgender'}
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_filename(filename):
    """Generate a unique filename with timestamp and UUID"""
    ext = filename.rsplit('.', 1)[1].lower()
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}.{ext}"

def async_route(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_recommendations', methods=['POST'])
@async_route
async def get_recommendations():
    try:
        # Form validation
        required_fields = ['gender', 'topwear_size', 'bottomwear_size', 'occasion', 'foot_size']
        for field in required_fields:
            if not request.form.get(field):
                flash(f'{field.replace("_", " ").title()} is required.', 'error')
                return redirect(url_for('index'))

        # Get form data directly
        gender = request.form.get('gender')
        topwear_size = request.form.get('topwear_size')
        bottomwear_size = request.form.get('bottomwear_size')
        occasion = request.form.get('occasion')
        foot_size = request.form.get('foot_size')
        skin_tone = request.form.get('skin_tone', 'unknown')
        custom_occasion = request.form.get('custom_occasion', '')
        image_path = None
        
        # Check if this is a traditional wear request
        if occasion.lower() == 'traditional':
            # Process traditional wear directly
            cultural_context = request.form.get('cultural_context')
            event_type = request.form.get('event_type')
            additional_info = request.form.get('additional_info', '')
            
            if not cultural_context or not event_type:
                flash('Please provide cultural context and event type for traditional wear.', 'error')
                return redirect(url_for('index'))
                
            # Combine all information for context
            traditional_context = {
                'cultural_context': cultural_context,
                'event_type': event_type,
                'gender': gender,
                'additional_info': additional_info
            }
            
            # Get traditional wear recommendations
            recommendations = await recommender.get_traditional_recommendations(traditional_context)
            
            # Store in session
            session['last_recommendations'] = {
                'data': recommendations,
                'timestamp': datetime.now().isoformat(),
                'is_traditional': True,
                'context': traditional_context
            }
            
            return render_template(
                'traditional_recommendations.html',
                recommendations=recommendations,
                context=traditional_context
            )

        # Handle image upload
        image = request.files.get('image')
        if image and image.filename:
            if not allowed_file(image.filename):
                flash('Invalid file type. Please upload a valid image.', 'error')
                return redirect(url_for('index'))

            try:
                filename = generate_unique_filename(secure_filename(image.filename))
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                logger.info(f"Image saved successfully: {image_path}")

                # Create relative path for template display
                relative_image_path = os.path.join('images/uploads', filename)
                
                # Detect skin tone from the image
                skin_tone = await recommender.detect_skin_tone(image_path)
                logger.info(f"Skin tone detected: {skin_tone}")
                
                # Extract additional image metadata for enhanced recommendations
                image_metadata = await recommender.extract_image_metadata(image_path)
                logger.info(f"Image metadata extracted: {len(image_metadata)} attributes found")
                
                # Analyze clothing items in the image
                clothing_items = await recommender.detect_clothing_items(image_path)
                if clothing_items:
                    logger.info(f"Detected {len(clothing_items)} clothing items in image")
                    
                # Add image data to the recommendation context
                recommendation_context = {
                    'skin_tone': skin_tone,
                    'detected_items': clothing_items,
                    'image_metadata': image_metadata,
                    'image_path': image_path,
                    'display_image': relative_image_path
                }
                
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                flash('Error processing image. Please try again.', 'error')
                return redirect(url_for('index'))

        try:
            # Get recommendations from the AI
            recommendations = await recommender.get_outfit_recommendations(
                gender=gender,
                topwear_size=topwear_size,
                bottomwear_size=bottomwear_size,
                skin_tone=skin_tone,
                occasion=occasion,
                foot_size=foot_size,
                image_path=image_path,
                custom_occasion=custom_occasion
            )

            # Store in session for sharing
            session['last_recommendations'] = {
                'data': recommendations,
                'timestamp': datetime.now().isoformat()
            }

            # Add recommendation_context if it exists
            context_data = {}
            if 'recommendation_context' in locals():
                context_data['recommendation_context'] = recommendation_context

            # Return HTML for regular form submissions
            return render_template(
                'recommendations.html',
                gender=gender,
                occasion=occasion,
                skin_tone=skin_tone,
                recommendations=recommendations,
                **context_data
            )

        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            flash('Error generating recommendations. Please try again.', 'error')
            return redirect(url_for('index'))

    except Exception as e:
        error_message = str(e)
        if "API quota exceeded" in error_message:
            flash("Our service is experiencing high demand. Please try again in a few minutes.", "warning")
        elif "API authentication" in error_message:
            flash("System configuration error. Please contact support.", "error")
            logging.error("API authentication error - check API key configuration")
        else:
            flash("Error generating recommendations. Please try again.", "error")
            logging.error(f"Error in get_recommendations: {error_message}")
        
        return redirect(url_for('index'))
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'An unexpected error occurred'})
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/share/<recommendation_id>')
def share_recommendation(recommendation_id):
    """Endpoint for sharing recommendations"""
    if 'last_recommendations' not in session:
        return jsonify({'error': 'Recommendations not found'}), 404
    
    return jsonify({
        'success': True,
        'share_url': url_for('view_shared', id=recommendation_id, _external=True)
    })

@app.route('/view/<id>')
def view_shared(id):
    """View shared recommendation"""
    if 'last_recommendations' not in session:
        flash('Shared recommendation not found or has expired.', 'error')
        return redirect(url_for('index'))
    
    recommendations = session['last_recommendations']['data']
    return render_template(
        'recommendations.html',
        recommendations=recommendations,
        shared=True
    )

@app.errorhandler(413)
def request_entity_too_large(error):
    flash('File too large. Maximum size is 5MB.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)