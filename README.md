# Calling Agent

A web application that allows users to initiate calls to customer service on their behalf, with features for real-time communication and call transcripts.

## Project Structure

This repository contains both the frontend and backend components of the Calling Agent application:

- `frontend/`: React application for the user interface
- `backend/`: Flask application for handling calls and API endpoints

## Getting Started

### Backend Setup

1. Navigate to the backend directory:

   ```
   cd backend
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Configure environment variables:

   - Update the values in `.env` with your Twilio credentials and other configuration

4. Run the backend:
   ```
   python app.py
   ```

### Frontend Setup

1. Navigate to the frontend directory:

   ```
   cd frontend
   ```

2. Install dependencies:

   ```
   npm install
   ```

3. Run the development server:
   ```
   npm run dev
   ```

## Features

- User-friendly interface for initiating calls
- Real-time call status updates
- Live text input for sending messages during calls
- Call transcript display
- Support for both flight and hotel operations

## License

MIT
