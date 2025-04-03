# Visual Quiz

A Streamlit-based quiz application that helps language learners practice Spanish vocabulary through AI-generated images.

## 🎯 Business Goals

- Provide an engaging visual quiz to help language learners practice Spanish vocabulary
- Integrate seamlessly with the lang-portal ecosystem
- Generate and cache AI images to create an efficient and cost-effective learning experience
- Track student performance through the lang-portal's review system

## 🚀 Features

- Generates AI images for Spanish vocabulary words using AWS Bedrock Canvas
- Implements a multiple-choice quiz format with 4 options per question
- Caches generated images to improve performance and reduce costs
- Tracks and submits quiz results back to lang-portal
- Provides immediate feedback on answers
- Shows final score and allows retrying the quiz

## ⚙️ Technical Implementation

### Integration with Lang Portal
- Receives `session_id` and `group_id` as URL parameters
- Fetches word groups from lang-portal API
- Submits review results back to lang-portal for tracking

### Image Generation
- Uses AWS Bedrock's Titan Image Generator model
- Implements file-based caching using MD5 hashes of words
- Generates minimalist, clear illustrations optimized for learning

### Quiz Flow
1. Fetches words from the specified group
2. Selects 4 random words for each quiz session
3. Generates/retrieves images for selected words
4. Presents multiple-choice questions with images
5. Provides immediate feedback and scoring
6. Submits results to lang-portal

## 🛠️ Setup & Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure AWS access using aws-vault:
```bash
# Add your AWS profile
aws-vault add myprofile

# Execute the app with aws-vault
aws-vault exec myprofile -- streamlit run app.py
```

3. Configure environment variables in `.env`:
```env
LANG_PORTAL_API_URL=http://127.0.0.1:5001  # Default for local development
```

4. Access the app at:
```
http://localhost:8085/?group_id=<group_id>&session_id=<session_id>
```

## 📦 Project Structure

```
visual-quiz/
├── app.py              # Main application code
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
├── .streamlit/        # Streamlit configuration
│   └── config.toml
├── cache/             # Image cache directory
└── README.md
```

## 🔧 Technical Requirements

- Python 3.12
- Streamlit
- AWS Bedrock with Titan Image Generator
- PIL for image handling
- Internet connection for API access
- aws-vault for AWS credentials management

## 🎨 Design Decisions

1. **Image Caching**: Implements a file-based cache to store generated images, reducing API calls and costs
2. **Error Handling**: Robust error handling for API calls and image generation
3. **User Feedback**: Immediate feedback on answers with correct/incorrect indicators
4. **Responsive Layout**: Uses Streamlit columns for a clean, responsive design
5. **Session Management**: Maintains quiz state using Streamlit's session state

## 🔄 Integration Points

- **Lang Portal API Endpoints**:
  - `GET /api/groups/{group_id}/words`: Fetches word list
  - `POST /api/study_sessions/{session_id}/words/{word_id}/review`: Submits results

## 🚧 Future Improvements

1. Add difficulty levels for word selection
2. Implement spaced repetition
3. Add support for multiple languages
4. Enhance image generation prompts for better quality
5. Add progress tracking and statistics
6. Implement user preferences for quiz length


---

## ⚙️ Technical Challenges & Uncertainties

1. What LLM model should we use to generate the images?
2. How fast is the image generation?
3. It would be beneficial to have a caching mechanism for the images, so that we reduce the costs.


---

## 🚧 Technical Constraints & Requirements

- Python 3.12
- Streamlit
- AWS Bedrock with Nova Models


---

## 📦 Project Structure

visual-quiz/
    ├── app.py
    ├── utils.py
    ├── requirements.txt
    └── README.md

## 🚀 Running the App

### 1. Start Lang Portal Backend
First, ensure the lang-portal backend is running:

```bash
# Initialize the database (only needed once or after schema changes)
cd lang-portal/backend-flask
invoke init-db

# Start the backend server
python app.py
```

The backend will run on http://127.0.0.1:5001

### 2. Start Visual Quiz App
In a new terminal:

```bash
# Using aws-vault for AWS credentials
cd visual-quiz
aws-vault exec myprofile -- streamlit run app.py
```

The app will be available at http://localhost:8085

### 3. Access the App
Access the app through the lang-portal interface, or directly with required parameters:
```
http://localhost:8085/?group_id=<group_id>&session_id=<session_id>
```

### 4. Development
For development and testing:

```bash
# Run tests
cd lang-portal/backend-flask
python -m pytest

# Run specific test file
python -m pytest tests/test_db_setup.py

# Run with verbose output
python -m pytest -v
```


