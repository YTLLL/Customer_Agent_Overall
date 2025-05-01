import json
import logging
import os
from datetime import datetime
from urllib.parse import quote

import boto3
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.rest import Client
from twilio.twiml.voice_response import Say, Start, Stream, VoiceResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
# Update CORS configuration to allow requests from your frontend
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "https://de38-2600-1700-1420-d200-318d-c888-d595-c06.ngrok-free.app",
                "http://localhost:5173",  # Add your frontend local development URL if needed
                "http://127.0.0.1:5173",  # Add your frontend local development URL if needed
            ],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    },
)

REQUIRED_ENV = [
    "TWILIO_ACCOUNT_SID",
    "TWILIO_API_KEY_SID",
    "TWILIO_API_KEY_SECRET",
    "TWILIO_TWIML_APP_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER",
    "YOUR_SERVER_URL",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",
]

for var in REQUIRED_ENV:
    if not os.getenv(var):
        raise EnvironmentError(f"Missing required environment variable: {var}")

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

# Initialize AWS clients
polly_client = boto3.client(
    "polly",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)

# In-memory store for call transcripts (would use a database in production)
call_transcripts = {}


@app.route("/token", methods=["GET"])
def generate_token():
    logger.info("Received token request")
    identity = request.args.get(
        "identity", "default_user"
    )  # Default identity if none provided
    try:
        token = AccessToken(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_API_KEY_SID"),
            os.getenv("TWILIO_API_KEY_SECRET"),
            identity=identity,
        )

        voice_grant = VoiceGrant(
            outgoing_application_sid=os.getenv("TWILIO_TWIML_APP_SID"),
            incoming_allow=True,
        )
        token.add_grant(voice_grant)
        token_str = token.to_jwt()
        logger.info(f"Generated token for identity: {identity}")

        return jsonify({"token": token_str})
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        return jsonify({"error": str(e)}), 500


call_messages = {}


import xml.etree.ElementTree as ET

from twilio.twiml.voice_response import Record, Say, Start, VoiceResponse


@app.route("/speak-text", methods=["POST"])
def speak_text():
    call_sid = request.form.get("CallSid")
    YOUR_SERVER_URL = os.getenv("YOUR_SERVER_URL")

    # Basic error if CallSid missing
    if not call_sid:
        response = VoiceResponse()
        response.say("Sorry, there was a problem identifying your call.", voice="woman")
        twiml = str(response)
        print("Generated TwiML:", twiml)
        return twiml, 200, {"Content-Type": "application/xml"}

    # Get message text
    text = call_messages.get(call_sid, "No message available for this call.")

    # Create standard TwiML first (WITHOUT Start)
    response = VoiceResponse()
    response.say(text, voice="woman")
    response.record(
        action=f"{YOUR_SERVER_URL}/recording-status",
        transcribe=True,
        transcribeCallback=f"{YOUR_SERVER_URL}/transcription",
        maxLength=60,
        playBeep=True,
    )
    response.say("Thank you for your response.", voice="woman")

    # Convert to string
    twiml = str(response)

    # Inject <Start><Transcription> manually right after <Response>
    start_transcription_xml = f"""<Start><Transcription url="{YOUR_SERVER_URL}/live-transcription-callback" method="POST" /></Start>"""
    # Insert after first <Response> tag
    twiml = twiml.replace("<Response>", f"<Response>{start_transcription_xml}", 1)

    # Log final TwiML
    print("Generated TwiML:", twiml)

    return twiml, 200, {"Content-Type": "application/xml"}


@app.route("/call", methods=["POST"])
def initiate_call():
    logger.info("Received call request")
    try:
        data = request.json
        logger.info(f"Call request data: {data}")
        to_number = data["to"]  # This will be +19098599810
        text = data.get("text", "")
        from_number = os.getenv("TWILIO_PHONE_NUMBER")

        # Set up TwiML for the call
        twiml = VoiceResponse()

        # First, gather any key press
        gather = twiml.gather(
            num_digits=1,
            action=f"{os.getenv('YOUR_SERVER_URL')}/speak-text",
            method="POST",
        )

        # Add initial instructions
        twiml.say("Press any key to hear the message.", voice="woman")

        # Add a fallback in case no key is pressed
        twiml.redirect(f"{os.getenv('YOUR_SERVER_URL')}/speak-text")

        # Store the text to speak in a session or temporary storage
        # For simplicity, we'll use a global dictionary
        global call_messages
        call_messages = {}

        # Create the call
        call = client.calls.create(to=to_number, from_=from_number, twiml=str(twiml))

        # Store the message for this call
        call_messages[call.sid] = text

        # Initialize empty transcript for this call
        call_transcripts[call.sid] = []

        return jsonify(
            {"status": "success", "call_sid": call.sid, "message": "Call initiated"}
        )
    except Exception as e:
        print(f"Error initiating call: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/send-text", methods=["POST"])
def handle_live_text():
    logger.info("Received send-text request")
    data = request.json
    logger.info(f"Send-text request data: {data}")
    call_sid = data["callSid"]
    text = data["text"]

    try:
        # Use Amazon Polly to synthesize speech
        response = polly_client.synthesize_speech(
            Text=text, OutputFormat="mp3", VoiceId="Joanna"  # English US female voice
        )

        if "AudioStream" in response:
            # Save the audio file locally
            audio_file_path = (
                f"static/polly_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
            )
            with open(audio_file_path, "wb") as file:
                file.write(response["AudioStream"].read())

            # URL to the audio file
            audio_url = f"{os.getenv('YOUR_SERVER_URL')}/{audio_file_path}"

            # Update the call with TwiML to play the audio
            twiml = VoiceResponse()
            twiml.play(audio_url)
            client.calls(call_sid).update(twiml=str(twiml))
        else:
            # Fallback to TwiML Say
            twiml = VoiceResponse()
            twiml.say(text, voice="woman")
            client.calls(call_sid).update(twiml=str(twiml))

        # Store the message as a "sent" transcript
        if call_sid in call_transcripts:
            call_transcripts[call_sid].append(
                {
                    "text": f"[Agent]: {text}",
                    "timestamp": datetime.now().isoformat(),
                    "type": "sent",
                }
            )

        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error sending text: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/live-transcription-callback", methods=["POST"])
def live_transcription_callback():
    logger.info("Received live transcription callback")
    logger.info(f"Live transcription data: {request.form}")

    call_sid = request.form.get("CallSid")
    transcription_text = request.form.get("TranscriptionText")

    if call_sid and transcription_text:
        if call_sid in call_transcripts:
            call_transcripts[call_sid].append(
                {
                    "text": f"[Customer-Live]: {transcription_text}",
                    "timestamp": datetime.now().isoformat(),
                    "type": "received",
                }
            )
        else:
            call_transcripts[call_sid] = [
                {
                    "text": f"[Customer-Live]: {transcription_text}",
                    "timestamp": datetime.now().isoformat(),
                    "type": "received",
                }
            ]
        logger.info(f"Added live transcription to call {call_sid}")
    else:
        logger.warning("Missing CallSid or TranscriptionText in live transcription")

    return "", 200


@app.route("/transcription", methods=["POST"])
def handle_transcription():
    """Handle transcription callbacks from Twilio"""
    logger.info("==== TRANSCRIPTION WEBHOOK CALLED ====")
    logger.info(f"Raw form data: {dict(request.form)}")

    call_sid = request.form.get("CallSid")
    transcript_text = request.form.get("TranscriptionText")
    transcription_status = request.form.get("TranscriptionStatus")

    logger.info(f"Call SID: {call_sid}")
    logger.info(f"Transcription Text: {transcript_text}")
    logger.info(f"Transcription Status: {transcription_status}")

    if call_sid and transcript_text:
        # Store the transcription
        if call_sid in call_transcripts:
            call_transcripts[call_sid].append(
                {
                    "text": f"[Customer]: {transcript_text}",
                    "timestamp": datetime.now().isoformat(),
                    "type": "received",
                }
            )
            logger.info(f"Added transcription to existing call {call_sid}")
        else:
            call_transcripts[call_sid] = [
                {
                    "text": f"[Customer]: {transcript_text}",
                    "timestamp": datetime.now().isoformat(),
                    "type": "received",
                }
            ]
            logger.info(f"Created new transcript for call {call_sid}")
    else:
        logger.warning("Missing CallSid or TranscriptionText in webhook data")

    return "", 200


@app.route("/transcripts", methods=["GET"])
def get_transcripts():
    """Return transcripts for a specific call"""
    logger.info("Received transcripts request")
    call_sid = request.args.get("callSid")
    logger.info(f"Requesting transcripts for call: {call_sid}")
    if not call_sid:
        return jsonify({"error": "CallSid is required"}), 400

    transcripts = call_transcripts.get(call_sid, [])
    return jsonify({"transcripts": transcripts})


@app.route("/call-status", methods=["GET"])
def get_call_status():
    """Get the status of a specific call"""
    logger.info("Received call-status request")
    call_sid = request.args.get("callSid")
    logger.info(f"Requesting status for call: {call_sid}")
    if not call_sid:
        return jsonify({"error": "CallSid is required"}), 400

    try:
        call = client.calls(call_sid).fetch()
        return jsonify({"status": call.status})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate_prompt", methods=["POST"])
def generate_prompt():
    try:
        data = request.json
        user_id = data.get("userId", "")
        name = data.get("name", "")
        phone_number = data.get("phoneNumber", "")
        other_info = data.get("otherPersonalInfo", "")

        # Check which type of info we received
        if "flightInfo" in data:
            info_type = "flight"
            info_name = data["flightInfo"].get("name", "")
            details = data["flightInfo"].get("details", "")
        elif "hotelInfo" in data:
            info_type = "hotel"
            info_name = data["hotelInfo"].get("name", "")
            details = data["hotelInfo"].get("details", "")
        else:
            return jsonify({"error": "Missing flight or hotel information"}), 400

        # Log the data received
        print(f"Received data: {info_type} request from {name}")
        print(f"Information: {info_name}")
        print(f"Details: {details}")

        # In a production app, you would store this in a database

        return jsonify(
            {"message": "Prompt generated successfully", "status": "success"}
        )
    except Exception as e:
        print(f"Error generating prompt: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/end-call", methods=["POST"])
def end_call():
    """End an in-progress call"""
    logger.info("Received end-call request")
    try:
        data = request.json
        logger.info(f"End-call request data: {data}")
        call_sid = data["callSid"]
        client.calls(call_sid).update(status="completed")
        return jsonify({"status": "success", "message": "Call ended"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


from twilio.twiml.voice_response import VoiceResponse


@app.route("/recording-status", methods=["POST"])
def recording_status_callback():
    """Handle recording status callbacks from Twilio"""
    logger.info("Received recording-status callback")
    logger.info(f"Recording status data: {request.form}")
    print("==== RECORDING STATUS WEBHOOK CALLED ====")
    print(f"Form data: {dict(request.form)}")
    recording_sid = request.form.get("RecordingSid")
    recording_url = request.form.get("RecordingUrl")
    call_sid = request.form.get("CallSid")

    print(f"Recording {recording_sid} completed for call {call_sid}")
    print(f"Recording URL: {recording_url}")

    # Proper XML response
    response = VoiceResponse()
    return str(response), 200, {"Content-Type": "application/xml"}


@app.route("/voice", methods=["GET", "POST"])
def voice_response():
    """Generate TwiML for incoming calls"""
    logger.info("Received voice response request")
    text = request.args.get("text", "Hello, this is a test call")
    logger.info(f"Voice response text: {text}")
    response = VoiceResponse()
    response.say(text, voice="woman")
    return str(response), 200, {"Content-Type": "application/xml"}


@app.errorhandler(Exception)
def handle_exception(e):
    # Log the error
    print(f"Unhandled exception: {str(e)}")
    # Return JSON instead of HTML for HTTP errors
    return jsonify({"error": str(e)}), 500


# Add this after loading the .env file
if (
    os.getenv("YOUR_SERVER_URL")
    != "https://de38-2600-1700-1420-d200-318d-c888-d595-c06.ngrok-free.app"
):
    print("Warning: YOUR_SERVER_URL in .env doesn't match your current ngrok URL")
    print(f"Current set URL: {os.getenv('YOUR_SERVER_URL')}")
    print("Consider updating your .env file")


@app.route("/", methods=["GET"])
def index():
    logger.info("Received index request")
    return "Twilio Voice App is running!", 200


# Ensure the static directory exists
os.makedirs("static", exist_ok=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
