import React, { useEffect, useState } from "react";
import { Box, Typography, TextField, Button, Paper } from "@mui/material";

const TwilioVoice = ({
  phoneNumber,
  initialText,
  onCallStarted,
  onCallEnded,
  onError,
}) => {
  const [status, setStatus] = useState("Ready to call");
  const [isCalling, setIsCalling] = useState(false);
  const [liveText, setLiveText] = useState("");
  const [callSid, setCallSid] = useState("");
  const [callTranscript, setCallTranscript] = useState([]);

  // Set initial text-to-speech from props
  const [textToSpeech, setTextToSpeech] = useState(initialText || "");

  const startCall = async () => {
    if (!phoneNumber) {
      setStatus("No phone number provided");
      return;
    }

    try {
      setIsCalling(true);
      setStatus("Connecting...");

      // Make API call to start the call
      const response = await fetch("http://localhost:5000/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to: phoneNumber,
          text: textToSpeech,
        }),
      });

      const result = await response.json();

      if (result.status !== "success") {
        throw new Error(result.error || "Failed to initiate call");
      }

      setCallSid(result.call_sid);
      setStatus("Call in progress...");
      onCallStarted?.();

      // Start listening for transcripts (this would be a WebSocket in a real app)
      startTranscriptPolling();
    } catch (error) {
      console.error("Call failed:", error);
      setStatus(`Call failed: ${error.message}`);
      setIsCalling(false);
      onError?.(error);
    }
  };

  const endCall = async () => {
    try {
      if (callSid) {
        await fetch("http://localhost:5000/end-call", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ callSid }),
        });
      }

      setIsCalling(false);
      setStatus("Call ended");
      onCallEnded?.();
    } catch (error) {
      console.error("Error ending call:", error);
      setStatus("Error ending call");
      onError?.(error);
    }
  };

  const sendLiveText = async () => {
    if (!callSid || !liveText) return;

    try {
      await fetch("http://localhost:5000/send-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          callSid: callSid,
          text: liveText,
        }),
      });

      // Add to transcript
      setCallTranscript((prev) => [
        ...prev,
        {
          type: "agent",
          text: liveText,
          timestamp: new Date().toISOString(),
        },
      ]);

      setLiveText("");
    } catch (error) {
      console.error("Failed to send text:", error);
      setStatus("Error sending text");
    }
  };

  // In a real app, this would be replaced with a WebSocket connection
  // This is just for demo purposes
  const startTranscriptPolling = () => {
    // Simulate receiving transcripts from the call
    const intervalId = setInterval(() => {
      if (!isCalling) {
        clearInterval(intervalId);
        return;
      }

      // Simulate receiving a transcript
      const randomResponses = [
        "I need to check my system for your booking.",
        "Could you please confirm your booking reference?",
        "I understand you'd like to cancel your reservation.",
        "I'll process that cancellation for you right away.",
        "Is there a particular reason you're cancelling?",
        "Let me check our policy on refunds for your booking.",
      ];

      const randomResponse =
        randomResponses[Math.floor(Math.random() * randomResponses.length)];

      // Add to transcript
      setCallTranscript((prev) => [
        ...prev,
        {
          type: "caller",
          text: randomResponse,
          timestamp: new Date().toISOString(),
        },
      ]);
    }, 5000); // Add a new transcript every 5 seconds

    return () => clearInterval(intervalId);
  };

  return (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Call Controls */}
      <Box sx={{ mb: 3 }}>
        <Button
          variant="contained"
          color={isCalling ? "error" : "primary"}
          onClick={isCalling ? endCall : startCall}
          sx={{
            px: 3,
            py: 1,
            backgroundColor: isCalling ? "#ff4444" : "#00e676",
            color: "white",
          }}
        >
          {isCalling ? "End Call" : "Start Call"}
        </Button>
        <Typography
          variant="body2"
          sx={{ mt: 1, color: "rgba(255,255,255,0.7)" }}
        >
          Status: {status}
        </Typography>
      </Box>

      {/* Transcript Display */}
      <Paper
        sx={{
          flex: 1,
          mb: 3,
          p: 2,
          bgcolor: "rgba(0,0,0,0.2)",
          overflowY: "auto",
          borderRadius: 1,
        }}
      >
        <Typography variant="subtitle2" gutterBottom>
          Call Transcript:
        </Typography>

        {callTranscript.length > 0 ? (
          callTranscript.map((entry, index) => (
            <Box
              key={index}
              sx={{
                mb: 2,
                pl: 1,
                borderLeft:
                  entry.type === "agent"
                    ? "3px solid #00e676"
                    : "3px solid #f4f4f4",
              }}
            >
              <Typography
                variant="caption"
                display="block"
                sx={{ mb: 0.5, color: "rgba(255,255,255,0.5)" }}
              >
                {entry.type === "agent" ? "Agent" : "Caller"} -{" "}
                {new Date(entry.timestamp).toLocaleTimeString()}
              </Typography>
              <Typography variant="body2">{entry.text}</Typography>
            </Box>
          ))
        ) : (
          <Typography
            variant="body2"
            sx={{ color: "rgba(255,255,255,0.5)", fontStyle: "italic" }}
          >
            Transcript will appear here when the call starts...
          </Typography>
        )}
      </Paper>

      {/* Live Text Input */}
      {isCalling && (
        <Box sx={{ display: "flex", gap: 1 }}>
          <TextField
            fullWidth
            variant="outlined"
            size="small"
            value={liveText}
            onChange={(e) => setLiveText(e.target.value)}
            placeholder="Type to speak in the call..."
            onKeyPress={(e) => e.key === "Enter" && sendLiveText()}
          />
          <Button
            variant="contained"
            onClick={sendLiveText}
            disabled={!liveText.trim()}
            sx={{ bgcolor: "#00e676" }}
          >
            Send
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default TwilioVoice;
