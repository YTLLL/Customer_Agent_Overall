# Calling Agent Backend

This is the backend service for the Calling Agent application. It provides API endpoints for initiating calls, sending text messages, and retrieving call status and transcripts.

## Setup

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Configure environment variables:

   - Copy `.env.example` to `.env` (if not already done)
   - Update the values in `.env` with your Twilio credentials and other configuration

3. Run the application:
   ```
   python app.py
   ```

## API Endpoints

- `POST /call`: Initiates a call to a specified phone number
- `GET /call-status`: Retrieves the status of a call
- `GET /transcripts`: Retrieves transcripts for a call
- `POST /send-text`: Sends text to be spoken during a call
- `POST /end-call`: Ends an active call
- `POST /api/generate_prompt`: Generates a prompt based on user information

## Environment Variables

- `TWILIO_ACCOUNT_SID`: Your Twilio Account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number
- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI for prompt generation)
