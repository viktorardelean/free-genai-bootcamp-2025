# Technical Specifications

## Initial Setup
Upon initialization, the application must perform the following actions:

- Fetch data from the endpoint `GET localhost:5001/api/groups/:id/raw`. This endpoint returns a JSON collection containing Spanish words and their corresponding English translations.
- Store this retrieved word collection in memory for efficient access throughout the session.

## Application States

This section outlines the states and corresponding user interactions within the single-page application.

### Setup State
- When the user first launches the application, they will be presented with a single button labeled **"Generate Sentence"**.
- Upon clicking this button, the application will:
  - Generate a new Spanish sentence using the Sentence Generator LLM.
  - Transition to the **Practice State**.

### Practice State
- In the Practice State, the user interface will display:
  - A generated Spanish sentence.
  - An upload field prompting users to upload an image related to the sentence.
  - A button labeled **"Submit for Review"**.
- When the user clicks "Submit for Review":
  - The uploaded image is sent to the Grading System.
  - The application transitions to the **Review State**.

### Review State
- During the Review State, users will see:
  - The original Spanish sentence.
  - Feedback from the Grading System, including:
    - **Image Transcription**: Extracted text from the uploaded image.
    - **Translation**: English translation of the transcription.
    - **Grading**:
      - A letter grade based on a numeric scale (1–10).
      - Detailed feedback assessing accuracy relative to the original sentence and suggestions for improvement.
  - A button labeled **"Next Sentence"**.
- Clicking "Next Sentence" will generate a new sentence and return the user to the **Practice State**.

## Sentence Generator LLM Prompt Guidelines
The Sentence Generator LLM should produce simple, grammatically correct sentences suitable for A1-level learners, using the following structure:

**Prompt:**  
"Generate a simple sentence using the following word: {{word}}. Grammar and vocabulary must align with A1-level proficiency."

**Allowed Vocabulary Categories:**
- **Objects**: e.g., book, car, house, phone
- **Actions**: e.g., read, drive, eat, sleep
- **Adjectives**: e.g., red, big, hot, cold
- **Adverbs**: e.g., quickly, slowly, loudly, quietly
- **Conjunctions**: e.g., and, but, or, if
- **Prepositions**: e.g., in, on, at, by
- **Interjections**: e.g., wow, hello, goodbye, thank you
- **Pronouns**: e.g., I, you, he, she, it, we, they
- **Determiners**: e.g., the, a, an
- **Quantifiers**: e.g., many, few, some, any
- **Modal Verbs**: e.g., can, could, may, might
- **Auxiliary Verbs**: e.g., is, was, were, will, would
- **Linking Verbs**: e.g., am, are, is, was, were
- **Temporal Adverbs**: e.g., now, then, always, never

