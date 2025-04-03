import streamlit as st
import requests
import os
import json
import logging
import random
import boto3
from botocore.config import Config
from dotenv import load_dotenv
import base64
from PIL import Image
import io
import hashlib
import time
from pathlib import Path
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get API URL from environment variable with a default for local development
API_URL = os.getenv('LANG_PORTAL_API_URL', 'http://127.0.0.1:5001')

# AWS Bedrock setup
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1',
    config=Config(retries=dict(max_attempts=3))
)

# Create cache directory if it doesn't exist
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

def get_cache_path(spanish_word: str, english_word: str) -> Path:
    """Generate a cache file path for a word pair"""
    # Create hash from both words to ensure uniqueness
    hash_name = hashlib.md5(f"{spanish_word}_{english_word}".encode()).hexdigest()
    return CACHE_DIR / f"{hash_name}.jpg"

def generate_image(spanish_word: str, english_word: str, cache: bool = True) -> Image.Image:
    """Generate an image for a word using AWS Bedrock Nova Canvas model"""
    if cache:
        cache_path = get_cache_path(spanish_word, english_word)
        if cache_path.exists():
            logger.info(f"Using cached image for word: {spanish_word} ({english_word})")
            return Image.open(cache_path)

    try:
        prompt = f"""Create a simple, clear illustration of a '{english_word}' on a white background.
The image should be minimalist and easily recognizable for language learning purposes."""
        
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
                "negativeText": "text, words, letters, numbers, watermark, signature, complex background, busy, cluttered",
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "height": 320,
                "width": 320,
                "cfgScale": 8.0,
                "seed": random.randint(1, 1000000)
            }
        }

        logger.info(f"Generating image for word: {spanish_word} ({english_word})")
        response = bedrock.invoke_model(
            modelId='amazon.nova-canvas-v1:0',
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())
        
        # Nova Canvas returns base64 image in images array
        base64_image = response_body.get("images")[0]
        base64_bytes = base64_image.encode('ascii')
        image_bytes = base64.b64decode(base64_bytes)
        image = Image.open(io.BytesIO(image_bytes))

        if cache:
            logger.info(f"Caching image for word: {spanish_word} ({english_word})")
            image.save(cache_path, "JPEG")

        return image

    except Exception as e:
        logger.error(f"Error generating image for word '{spanish_word} ({english_word})': {str(e)}")
        logger.error(f"Full error: {traceback.format_exc()}")
        return None

def fetch_words(api_url: str = API_URL) -> list:
    """Fetch words from API"""
    group_id = st.query_params.get('group_id')
    session_id = st.query_params.get('session_id')
    
    if not group_id:
        st.error("No group_id provided in URL")
        return None
    
    try:
        url = f"{api_url}/api/groups/{group_id}/words"
        logger.info(f"Fetching words from: {url}")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Extract words from paginated response
        words = data.get('words', [])
        
        # Store IDs in session state
        st.session_state.group_id = group_id
        st.session_state.session_id = session_id
        
        logger.info(f"Fetched {len(words)} words")
        logger.debug(f"Words data structure: {words[:2]}")  # Log first 2 words
        return words
    except requests.RequestException as e:
        logger.error(f"Error fetching words: {str(e)}")
        st.error("Failed to fetch words from the server. Please try again later.")
        return None

def submit_review_result(word_id: int, is_correct: bool):
    """Submit review result back to the API"""
    try:
        url = f"{API_URL}/api/study_sessions/{st.session_state.session_id}/words/{word_id}/review"
        logger.info(f"Submitting review - Word ID: {word_id}, Correct: {is_correct}")
        response = requests.post(url, json={"correct": is_correct})
        response.raise_for_status()
        logger.info("Review submitted successfully")
    except requests.RequestException as e:
        logger.error(f"Error submitting review: {str(e)}")
        st.warning("Failed to save your answer, but you can continue with the quiz.")

def initialize_quiz():
    """Initialize a new quiz session"""
    try:
        params = st.query_params
        group_id = params.get('group_id')
        session_id = params.get('session_id')
        
        if not group_id or not session_id:
            st.error("Missing required parameters. Please access this app through the lang-portal or provide group_id and session_id in the URL.")
            st.info("Example URL: http://localhost:8085/?group_id=1&session_id=123")
            return False
        
        # Fetch words for the group
        url = f"{API_URL}/api/groups/{group_id}/words"
        logger.info(f"Fetching words from: {url}")
        
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Extract words from paginated response
        words = data.get('words', [])
        
        logger.info(f"Received {len(words)} words")
        
        if not words:
            st.error("No words available for this group")
            return False
            
        # Always try to get 4 questions
        num_questions = min(4, len(words))
        logger.info(f"Will create {num_questions} questions")
        
        quiz_words = random.sample(words, num_questions)
        logger.info(f"Selected {len(quiz_words)} words")
        
        # Generate/get images for each word
        quiz_images = []
        with st.spinner('Generating images...'):
            for word in quiz_words:
                image = generate_image(word['spanish'], word['english'])
                if image:
                    quiz_images.append((word, image))
        
        logger.info(f"Generated {len(quiz_images)} images")
        
        if len(quiz_images) < num_questions:
            st.error(f"Failed to generate all required images")
            return False
        
        # Store quiz data in session state
        st.session_state.quiz_words = [word for word, _ in quiz_images]
        st.session_state.quiz_images = quiz_images
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.total_questions = num_questions
        st.session_state.session_id = session_id
        
        logger.info(f"Quiz initialized with {st.session_state.total_questions} questions")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing quiz: {str(e)}")
        st.error(f"Failed to initialize quiz: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# Initialize session state
if 'words_data' not in st.session_state:
    st.session_state.words_data = fetch_words()

# Main app
st.title("Visual Quiz")
st.write("Match the images with their correct Spanish words!")

if 'quiz_initialized' not in st.session_state:
    st.session_state.quiz_initialized = False

if not st.session_state.quiz_initialized:
    st.info("Click 'Start Quiz' to begin testing your Spanish vocabulary!")
    if st.button("Start Quiz", use_container_width=True):
        if initialize_quiz():
            st.session_state.quiz_initialized = True
            st.rerun()

elif hasattr(st.session_state, 'quiz_images'):
    # Display progress
    progress = st.session_state.current_question / st.session_state.total_questions
    st.progress(progress)
    st.write(f"Question {min(st.session_state.current_question + 1, st.session_state.total_questions)} of {st.session_state.total_questions}")
    
    # Display current question
    if st.session_state.current_question < st.session_state.total_questions:
        current_image_data = st.session_state.quiz_images[st.session_state.current_question]
        correct_word = current_image_data[0]
        
        # Display image
        st.image(
            current_image_data[1], 
            caption="¿Qué es esto?", 
            use_container_width=True
        )
        
        # Create options from the words that have images
        options = [word['spanish'] for word in st.session_state.quiz_words]
        
        # Ensure options order stays consistent within a question
        if 'current_options' not in st.session_state:
            st.session_state.current_options = random.sample(options, len(options))
        
        # Create columns for options
        cols = st.columns(2)
        
        # Show options and handle answers
        answer_clicked = None
        
        for i, option in enumerate(st.session_state.current_options):
            if cols[i % 2].button(
                option,
                key=f"option_{i}_{st.session_state.current_question}",
                use_container_width=True,
                disabled='answer_submitted' in st.session_state
            ):
                answer_clicked = option
        
        # Handle answer submission
        if answer_clicked and 'answer_submitted' not in st.session_state:
            is_correct = answer_clicked == correct_word['spanish']
            submit_review_result(correct_word['id'], is_correct)
            
            st.session_state.answer_submitted = {
                'selected': answer_clicked,
                'correct': is_correct
            }
            
            if is_correct:
                st.session_state.score += 1
        
        # Show feedback if answered
        if 'answer_submitted' in st.session_state:
            if st.session_state.answer_submitted['correct']:
                st.success("¡Correcto! 🎉")
            else:
                st.error(f"¡Incorrecto! La respuesta correcta era: {correct_word['spanish']}")
            
            # Show next question button
            if st.button("Siguiente Pregunta ➡️", use_container_width=True):
                st.session_state.current_question += 1
                st.session_state.pop('answer_submitted', None)
                st.session_state.pop('current_options', None)
                st.rerun()
    
    else:
        # Quiz completed
        final_score = (st.session_state.score / st.session_state.total_questions) * 100
        st.success(f"¡Quiz completado! 🎉")
        st.write(f"Tu puntuación: {st.session_state.score}/{st.session_state.total_questions} ({final_score:.1f}%)")
        
        if st.button("¡Intentar de nuevo!", use_container_width=True):
            st.session_state.quiz_initialized = False
            st.session_state.pop('answer_submitted', None)
            st.session_state.pop('current_options', None)
            st.rerun() 