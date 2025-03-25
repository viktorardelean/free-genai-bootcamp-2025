import streamlit as st
import requests
import os
from PIL import Image
import io
import json
from typing import List, Dict
import logging
import random
import boto3
from botocore.config import Config
from dotenv import load_dotenv
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API URL from environment variable with a default for local development
API_URL = os.getenv('LANG_PORTAL_API_URL', 'http://127.0.0.1:5001')

# Initialize session state variables if they don't exist
if 'current_sentence' not in st.session_state:
    st.session_state.current_sentence = None
if 'state' not in st.session_state:
    st.session_state.state = 'setup'
if 'word_collection' not in st.session_state:
    st.session_state.word_collection = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'group_id' not in st.session_state:
    st.session_state.group_id = None

# AWS Bedrock setup
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1',  # or your preferred region
    config=Config(
        retries = dict(
            max_attempts = 3
        )
    )
)

# Initialize the Textract client
textract = boto3.client('textract')

def fetch_word_collection(api_url: str = API_URL) -> List[Dict]:
    """Fetch word collection from API"""
    # Get parameters from URL query parameters
    group_id = st.query_params.get('group_id')
    session_id = st.query_params.get('session_id')
    
    # Store in session state
    st.session_state.group_id = group_id
    st.session_state.session_id = session_id
    
    logger.info(f"Group ID: {group_id}, Session ID: {session_id}")
    
    if not group_id:
        st.error("No group_id provided in URL")
        return []
    
    try:
        url = f"{api_url}/api/groups/{group_id}/words"
        logger.info(f"Fetching words from: {url}")
        
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        logger.info(f"Received {len(data)} words from API")
        logger.info(f"Response data: {data}")
        
        return data
    except requests.RequestException as e:
        error_msg = f"Error fetching words: {str(e)}"
        logger.error(error_msg)
        st.error(error_msg)
        return []

def call_bedrock(prompt: str) -> str:
    """Call Amazon Bedrock Nova Micro model"""
    try:
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ]
        }
        
        response = bedrock.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Read and decode the response
        response_body = json.loads(response['body'].read().decode())
        logger.info(f"Raw Bedrock response: {response_body}")
        
        # Extract the generated text from the response
        if 'output' in response_body and 'message' in response_body['output']:
            text = response_body['output']['message']['content'][0]['text']
            return text.strip()
        else:
            logger.error(f"Unexpected response format: {response_body}")
            return None
        
    except Exception as e:
        logger.error(f"Error calling Bedrock: {str(e)}")
        logger.error(f"Full error: {traceback.format_exc()}")
        return None

def generate_sentence() -> str:
    """Generate a new Spanish sentence using a random word from the collection"""
    if not st.session_state.word_collection:
        return "No words available."
    
    words = st.session_state.word_collection.get('words', [])
    if not words:
        return "No words available."
    
    word = random.choice(words)
    logger.info(f"Selected word for sentence: {word}")
    
    # Store the word ID for review submission
    st.session_state.current_word_id = word['id']
    
    prompt = f"""Generate a simple sentence using the Spanish word "{word['spanish']}" (English: {word['english']}).
The sentence must be at A1-level proficiency using only basic grammar and vocabulary.

Use only these elements:
- Basic verbs (is, has, likes, wants)
- Simple adjectives (big, small, good, bad)
- Basic prepositions (in, on, at)
- Common pronouns (I, you, he, she, it)
- Articles (the, a, an)

The sentence should be in Spanish, with 4-8 words maximum.
Return ONLY the Spanish sentence, nothing else.
"""

    # Call Bedrock for sentence generation
    sentence = call_bedrock(prompt)
    if not sentence:
        # Fallback to template sentences if API call fails
        sample_sentences = [
            f"El {word['spanish']} es grande.",
            f"Mi {word['spanish']} está aquí.",
            f"Yo tengo un {word['spanish']}.",
            f"El {word['spanish']} es bonito."
        ]
        sentence = random.choice(sample_sentences)
    
    logger.info(f"Generated sentence: {sentence}")
    return sentence.strip()

def grade_image(image, expected_sentence: str):
    """Grade the uploaded image using Amazon Textract"""
    try:
        # Convert PIL Image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=image.format or 'JPEG')
        img_bytes = img_byte_arr.getvalue()

        # Call Textract to detect text
        response = textract.detect_document_text(
            Document={'Bytes': img_bytes}
        )
        
        # Extract text from blocks
        detected_text = []
        for block in response['Blocks']:
            if block['BlockType'] == 'LINE':
                detected_text.append(block['Text'])
        
        transcribed_text = ' '.join(detected_text).strip()
        logger.info(f"Transcribed text: {transcribed_text}")
        
        # Compare with expected sentence (case-insensitive)
        is_match = transcribed_text.lower() == expected_sentence.lower()
        
        # Submit result if we have a session_id
        if st.session_state.session_id and hasattr(st.session_state, 'current_word_id'):
            submit_review_result(st.session_state.current_word_id, is_match)
        
        return {
            "transcription": transcribed_text,
            "expected": expected_sentence,
            "is_correct": is_match,
            "grade": "A" if is_match else "F",
            "score": 10 if is_match else 0,
            "feedback": (
                "Excellent! Your handwriting matches the sentence perfectly." 
                if is_match 
                else f"The text doesn't match. Expected: '{expected_sentence}', Got: '{transcribed_text}'"
            )
        }
        
    except Exception as e:
        logger.error(f"Error grading image: {str(e)}")
        logger.error(f"Full error: {traceback.format_exc()}")
        return {
            "transcription": "Error processing image",
            "expected": expected_sentence,
            "is_correct": False,
            "grade": "F",
            "score": 0,
            "feedback": f"Error processing image: {str(e)}"
        }

def submit_review_result(word_id: int, is_correct: bool):
    """Submit review result back to the API"""
    try:
        # Log session and word IDs
        logger.info(f"Attempting to submit review - Session ID: {st.session_state.session_id}, Word ID: {word_id}")
        
        url = f"{API_URL}/api/study_sessions/{st.session_state.session_id}/words/{word_id}/review"
        data = {
            "correct": is_correct
        }
        
        logger.info(f"Submitting review to {url} with data: {data}")
        response = requests.post(url, json=data)
        
        if response.status_code == 404:
            logger.error("404 Error - Session or word not found")
            logger.error(f"Response content: {response.text}")
        
        response.raise_for_status()
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
    except requests.RequestException as e:
        logger.error(f"Error submitting review: {str(e)}")
        logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response'}")

# Initialize the app
st.title("Spanish Writing Practice")

# Fetch word collection on first load
if st.session_state.word_collection is None:
    st.session_state.word_collection = fetch_word_collection()  # Use default API_URL

# Setup State
if st.session_state.state == 'setup':
    if st.button("Generate Sentence"):
        st.session_state.current_sentence = generate_sentence()
        st.session_state.state = 'practice'
        st.rerun()

# Practice State
elif st.session_state.state == 'practice':
    st.write("### Your Sentence:")
    st.write(st.session_state.current_sentence)
    
    # Add tabs for upload and camera
    tab1, tab2 = st.tabs(["📷 Take Photo", "📁 Upload Image"])
    
    with tab1:
        camera_photo = st.camera_input("Take a picture of your writing")
        if camera_photo and st.button("Submit Photo for Review", key="submit_photo"):
            image = Image.open(camera_photo)
            results = grade_image(image, st.session_state.current_sentence)
            st.session_state.review_results = results
            st.session_state.state = 'review'
            st.rerun()
    
    with tab2:
        uploaded_file = st.file_uploader("Upload your image", type=['png', 'jpg', 'jpeg'])
        if uploaded_file and st.button("Submit Upload for Review", key="submit_upload"):
            image = Image.open(uploaded_file)
            results = grade_image(image, st.session_state.current_sentence)
            st.session_state.review_results = results
            st.session_state.state = 'review'
            st.rerun()

# Review State
elif st.session_state.state == 'review':
    st.write("### Original Sentence:")
    st.write(st.session_state.current_sentence)
    
    st.write("### Feedback:")
    results = st.session_state.review_results
    
    st.write("**Image Transcription:**")
    st.write(results["transcription"])
    
    st.write("**Translation:**")
    st.write(results["expected"])
    
    st.write("**Grade:**", results["grade"])
    st.write("**Score:**", f"{results['score']}/10")
    
    st.write("**Feedback:**")
    st.write(results["feedback"])
    
    if st.button("Next Sentence"):
        st.session_state.current_sentence = generate_sentence()
        st.session_state.state = 'practice'
        st.rerun()

# Load environment variables
load_dotenv()
