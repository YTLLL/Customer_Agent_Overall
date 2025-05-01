import React, { useState, useEffect } from "react";
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Box,
  Typography,
  IconButton,
  AppBar,
  Toolbar,
  Container,
  Button,
  Avatar,
  Dialog,
  DialogContent,
  DialogActions,
  TextField,
  Paper,
  InputAdornment,
  Snackbar,
  Alert,
} from "@mui/material";
import GridViewIcon from "@mui/icons-material/GridView";
import NotificationsIcon from "@mui/icons-material/Notifications";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import AirplaneTicketIcon from "@mui/icons-material/AirplaneTicket";
import HotelIcon from "@mui/icons-material/Hotel";
import EditIcon from "@mui/icons-material/Edit";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import MicIcon from "@mui/icons-material/Mic";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import EventForm from "./components/EventForm/EventForm";
import "./App.css";

// Create a dark theme
const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#00e676",
    },
    background: {
      default: "#303030",
      paper: "#2a2a2a",
    },
  },
});

// Headset logo component
const HeadsetLogo = () => (
  <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12,1C7,1 3,5 3,10V17A3,3 0 0,0 6,20H9V12H5V10A7,7 0 0,1 12,3A7,7 0 0,1 19,10V12H15V20H18A3,3 0 0,0 21,17V10C21,5 17,1 12,1M7.5,21.5A1.5,1.5 0 0,0 9,23A1.5,1.5 0 0,0 10.5,21.5A1.5,1.5 0 0,0 9,20A1.5,1.5 0 0,0 7.5,21.5M16.5,21.5A1.5,1.5 0 0,0 18,23A1.5,1.5 0 0,0 19.5,21.5A1.5,1.5 0 0,0 18,20A1.5,1.5 0 0,0 16.5,21.5Z" />
    <circle cx="9.5" cy="10" r="1" fill="#303030" />
    <circle cx="14.5" cy="10" r="1" fill="#303030" />
  </svg>
);

// Component to display when a call is in progress
const CallInProgress = ({
  phoneNumber,
  callStartTime,
  onCancel,
  callStatus,
  callSid,
  onSendText,
  transcripts,
}) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [liveText, setLiveText] = useState("");

  // Update the timer every second
  useEffect(() => {
    const intervalId = setInterval(() => {
      const now = new Date();
      const seconds = Math.floor((now - callStartTime) / 1000);
      setElapsedTime(seconds);
    }, 1000);

    return () => clearInterval(intervalId);
  }, [callStartTime]);

  // Format elapsed time as mm:ss
  const formatTime = (totalSeconds) => {
    const minutes = Math.floor(totalSeconds / 60)
      .toString()
      .padStart(2, "0");
    const seconds = (totalSeconds % 60).toString().padStart(2, "0");
    return `${minutes}:${seconds}`;
  };

  // Handle sending live text
  const handleSendText = () => {
    if (liveText.trim() && callSid) {
      onSendText(liveText);
      setLiveText("");
    }
  };

  // Handle pressing enter in text field
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendText();
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        p: 2,
        width: "100%",
        maxWidth: "600px",
      }}
    >
      <Paper
        sx={{
          p: 2,
          bgcolor: "#00382f",
          borderRadius: 2,
          color: "white",
          mb: 3,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
          <Avatar sx={{ bgcolor: "#00e676", mr: 2 }}>
            <HeadsetLogo />
          </Avatar>
          <Box>
            <Typography
              variant="h5"
              sx={{ color: "#00e676", fontWeight: "bold" }}
            >
              {formatTime(elapsedTime)}
            </Typography>
            <Typography variant="body2">
              Calling American Express customer support
            </Typography>
          </Box>
        </Box>

        <Box sx={{ mt: 3, mb: 2 }}>
          <Typography variant="body2" sx={{ mb: 1 }}>
            {callStatus}
          </Typography>
          <Box
            sx={{
              height: "1px",
              bgcolor: "rgba(255,255,255,0.2)",
              width: "100%",
              my: 2,
            }}
          />
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
          <AccessTimeIcon
            sx={{ fontSize: 16, mr: 1, color: "rgba(255,255,255,0.7)" }}
          />
          <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.7)" }}>
            10 mins estimation
          </Typography>
        </Box>

        <Button
          variant="outlined"
          size="small"
          onClick={onCancel}
          sx={{
            mt: 2,
            color: "white",
            borderColor: "rgba(255,255,255,0.3)",
            "&:hover": {
              borderColor: "white",
              bgcolor: "rgba(255,255,255,0.1)",
            },
          }}
        >
          Cancel request
        </Button>
      </Paper>

      {/* Transcription Display */}
      {transcripts.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Call Transcription:
          </Typography>
          <Paper sx={{ p: 2, bgcolor: "rgba(0,0,0,0.2)", borderRadius: 1 }}>
            {transcripts.map((transcript, idx) => (
              <Typography key={idx} variant="body2" paragraph>
                {transcript.text}
              </Typography>
            ))}
          </Paper>
        </Box>
      )}

      {/* Live Text Input */}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        <Typography variant="caption" sx={{ fontWeight: "medium" }}>
          Send text to be spoken during the call:
        </Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <TextField
            fullWidth
            variant="outlined"
            size="small"
            value={liveText}
            onChange={(e) => setLiveText(e.target.value)}
            placeholder="Type text to speak during the call..."
            onKeyPress={handleKeyPress}
          />
          <Button
            variant="contained"
            color="primary"
            onClick={handleSendText}
            disabled={!liveText.trim() || !callSid}
          >
            Send
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

// ChatMessage component for message bubbles
const ChatMessage = ({ message, isUser }) => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        mb: 3,
      }}
    >
      {!isUser && (
        <Avatar
          sx={{
            bgcolor: "#00e676",
            width: 36,
            height: 36,
            mr: 1,
          }}
        >
          <HeadsetLogo />
        </Avatar>
      )}
      <Paper
        sx={{
          p: 2,
          maxWidth: "80%",
          bgcolor: isUser ? "transparent" : "#383838",
          border: isUser ? "1px solid rgba(255, 255, 255, 0.12)" : "none",
          borderRadius: 2,
          boxShadow: "none",
        }}
      >
        <Typography variant="body2" component="div" whiteSpace="pre-wrap">
          {message}
        </Typography>
      </Paper>
    </Box>
  );
};

function App() {
  // Form state variables
  const [callStartTime, setCallStartTime] = useState(null);
  const [open, setOpen] = useState(false);
  const [eventType, setEventType] = useState("Air ticket operations");
  const [description, setDescription] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [confirmed, setConfirmed] = useState(false);
  const [userName, setUserName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [countryCode, setCountryCode] = useState("+1");
  const [additionalInfo, setAdditionalInfo] = useState("");

  // Chat interface state
  const [showChatInterface, setShowChatInterface] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState([]);

  // Call state
  const [showCallInterface, setShowCallInterface] = useState(false);
  const [callScript, setCallScript] = useState("");
  const [callStatus, setCallStatus] = useState(
    "Explaining the reasons of cancellation..."
  );
  const [callSid, setCallSid] = useState("");
  const [transcripts, setTranscripts] = useState([]);

  // Alert state
  const [alert, setAlert] = useState({
    open: false,
    message: "",
    severity: "info",
  });

  // Dummy data to display after form submission
  const userInfoMessage = `Here is user info I collected:
1 order: xxxx
name: ${userName || "Ryan lei"}
DOB: xxx
${
  eventType === "Air ticket operations" ? "Flight" : "Hotel"
} Name: ${description}
Is this Order correct? If Yes I will store this Order`;

  const extraInfoMessage = `Here is extra info that I searched:
${eventType === "Air ticket operations" ? "Flight" : "Hotel"} details: ${
    additionalInfo || "Not provided"
  }
Website Address: www.example.com
Phone Number: ${countryCode}${phoneNumber || ""}`;

  const handleClickOpen = (type) => {
    setEventType(type);
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleCreate = () => {
    // Form validation
    if (!confirmed) {
      setAlert({
        open: true,
        message: "Please confirm the data usage terms before creating.",
        severity: "warning",
      });
      return;
    }

    if (!description) {
      setAlert({
        open: true,
        message: `Please enter ${
          eventType === "Air ticket operations" ? "flight name" : "hotel name"
        }.`,
        severity: "warning",
      });
      return;
    }

    if (!userName) {
      setAlert({
        open: true,
        message: "Please enter your name.",
        severity: "warning",
      });
      return;
    }

    // Generate a unique userId
    const uniqueUserId =
      Date.now().toString(36) + Math.random().toString(36).substr(2);

    // Create payload according to the required structure and rearranged form
    const payload = {
      userId: uniqueUserId,
      ...(eventType === "Air ticket operations"
        ? {
            flightInfo: {
              timestamp: Date.now(),
              name: description,
              details: additionalInfo,
            },
          }
        : {
            hotelInfo: {
              timestamp: new Date().toISOString(),
              name: description,
              details: additionalInfo,
            },
          }),
      phoneNumber: `${countryCode}${phoneNumber}`,
      name: userName,
      otherPersonalInfo: additionalInfo,
    };

    console.log("Sending payload to backend:", payload);

    // Send to backend with updated ngrok URL
    fetch("http://localhost:8000/api/generate_prompt", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("Success:", data);

        // Generate call script from the response or use a default
        const generatedScript = `Hello, this is calling on behalf of ${userName} regarding ${
          eventType === "Air ticket operations" ? "a flight" : "a hotel"
        } named ${description}. The customer would like to cancel their reservation. ${
          additionalInfo ? `Additional information: ${additionalInfo}` : ""
        }`;
        setCallScript(generatedScript);

        // Reset form and close dialog
        setUploadedFiles([]);
        setConfirmed(false);
        setOpen(false);

        // Show chat interface with response from backend
        setShowChatInterface(true);
        setMessages([
          { text: userInfoMessage, isUser: false },
          { text: extraInfoMessage, isUser: false },
        ]);
      })
      .catch((error) => {
        console.error("Error:", error);
        setAlert({
          open: true,
          message: "Error connecting to backend. Using test data instead.",
          severity: "error",
        });

        // For testing without backend
        const generatedScript = `Hello, this is calling on behalf of ${userName} regarding ${
          eventType === "Air ticket operations" ? "a flight" : "a hotel"
        } named ${description}. The customer would like to cancel their reservation. ${
          additionalInfo ? `Additional information: ${additionalInfo}` : ""
        }`;
        setCallScript(generatedScript);

        setUploadedFiles([]);
        setConfirmed(false);
        setOpen(false);
        setShowChatInterface(true);
        setMessages([
          { text: userInfoMessage, isUser: false },
          { text: extraInfoMessage, isUser: false },
        ]);
      });
  };

  const handleFileChange = (files) => {
    setUploadedFiles((prevFiles) => [...prevFiles, ...files]);
  };

  const handleBackToWelcome = () => {
    setShowChatInterface(false);
    setShowCallInterface(false);
    setMessages([]);
    // End any active call
    if (callSid) {
      handleEndCall();
    }
  };

  const handleSendMessage = () => {
    if (chatInput.trim() === "") return;

    // Add user message
    setMessages((prev) => [...prev, { text: chatInput, isUser: true }]);
    setChatInput("");

    // Simulate response based on user input
    setTimeout(() => {
      let responseText = "";

      if (
        chatInput.toLowerCase().includes("yes") ||
        chatInput.toLowerCase().includes("proceed")
      ) {
        responseText =
          "Great! I'll proceed with the cancellation. We'll make a call now to handle this for you.";

        // Show call interface after positive confirmation
        setTimeout(() => {
          handleStartCall();
        }, 1000);
      } else if (
        chatInput.toLowerCase().includes("no") ||
        chatInput.toLowerCase().includes("changed")
      ) {
        responseText =
          "No problem. I won't proceed with the cancellation. Is there anything else you need help with?";
      } else {
        responseText =
          "I'm not sure I understand. Would you like to proceed with the cancellation or not?";
      }

      setMessages((prev) => [...prev, { text: responseText, isUser: false }]);
    }, 1000);
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleProceedCancellation = () => {
    setMessages((prev) => [
      ...prev,
      { text: "Yes, proceed the cancellation.", isUser: true },
      {
        text: "We'll call the customer service on your behalf to handle the cancellation. You'll see updates here.",
        isUser: false,
      },
    ]);

    // Start the call
    handleStartCall();
  };

  // Function to start a call using Twilio - Updated with ngrok URL
  const handleStartCall = async () => {
    setCallStartTime(new Date());
    setShowCallInterface(true);
    setCallStatus("Connecting to customer service...");
    setTranscripts([]);

    try {
      // Make API call to start the call to the specific number
      const response = await fetch(
        "https://de38-2600-1700-1420-d200-318d-c888-d595-c06.ngrok-free.app/call",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            to: "+19098599810", // Use the specific number
            text: callScript,
          }),
        }
      );

      const result = await response.json();

      if (result.status !== "success") {
        throw new Error(result.error || "Failed to initiate call");
      }

      setCallSid(result.call_sid);
      setCallStatus("Explaining the reasons of cancellation...");

      // Start polling for call status and transcriptions
      startPolling(result.call_sid);
    } catch (error) {
      console.error("Call failed:", error);
      setCallStatus(`Call failed: ${error.message}`);
      setAlert({
        open: true,
        message: `Failed to start call: ${error.message}`,
        severity: "error",
      });
    }
  };

  // Function to poll for call status and transcriptions - Updated with ngrok URL
  const startPolling = (sid) => {
    // Set up interval to check call status
    const statusInterval = setInterval(async () => {
      try {
        const response = await fetch(
          `https://de38-2600-1700-1420-d200-318d-c888-d595-c06.ngrok-free.app/call-status?callSid=${sid}`
        );
        const data = await response.json();

        if (data.status !== "in-progress") {
          clearInterval(statusInterval);
          clearInterval(transcriptInterval);

          if (data.status === "completed") {
            setCallStatus("Call completed");
            // Add call summary to chat
            setMessages((prev) => [
              ...prev,
              {
                text: "✅ Call completed successfully. The cancellation has been processed.",
                isUser: false,
              },
            ]);
            // Reset call interface after delay
            setTimeout(() => {
              setShowCallInterface(false);
            }, 3000);
          } else if (data.status === "failed") {
            setCallStatus("Call failed");
            setAlert({
              open: true,
              message: "Call failed. Please try again later.",
              severity: "error",
            });
          }
        }
      } catch (error) {
        console.error("Error checking call status:", error);
      }
    }, 5000); // Check every 5 seconds

    // Set up interval to check for new transcriptions
    const transcriptInterval = setInterval(async () => {
      try {
        const response = await fetch(
          `https://de38-2600-1700-1420-d200-318d-c888-d595-c06.ngrok-free.app/transcripts?callSid=${sid}`
        );
        const data = await response.json();

        if (data.transcripts && data.transcripts.length > 0) {
          setTranscripts(data.transcripts);
        }
      } catch (error) {
        console.error("Error fetching transcripts:", error);
      }
    }, 2000); // Check every 2 seconds

    // Return cleanup function
    return () => {
      clearInterval(statusInterval);
      clearInterval(transcriptInterval);
    };
  };

  // Function to send live text during call - Updated with ngrok URL
  const handleSendLiveText = async (text) => {
    if (!callSid || !text) return;

    try {
      await fetch(
        "https://de38-2600-1700-1420-d200-318d-c888-d595-c06.ngrok-free.app/send-text",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            callSid: callSid,
            text: text,
          }),
        }
      );

      // Add to messages
      setMessages((prev) => [
        ...prev,
        {
          text: `[Sent to call]: ${text}`,
          isUser: true,
        },
      ]);
    } catch (error) {
      console.error("Failed to send text:", error);
      setAlert({
        open: true,
        message: "Failed to send text to call",
        severity: "error",
      });
    }
  };

  // Function to end call - Updated with ngrok URL
  const handleEndCall = async () => {
    if (!callSid) return;

    try {
      await fetch(
        "https://de38-2600-1700-1420-d200-318d-c888-d595-c06.ngrok-free.app/end-call",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ callSid }),
        }
      );

      setCallStatus("Call cancelled");

      // Add message about cancellation
      setMessages((prev) => [
        ...prev,
        {
          text: "Call cancelled. Is there anything else I can help you with?",
          isUser: false,
        },
      ]);

      // Reset call interface
      setShowCallInterface(false);
      setCallStartTime(null);
      setCallSid("");
      setTranscripts([]);
    } catch (error) {
      console.error("Error ending call:", error);
      setAlert({
        open: true,
        message: "Error ending call. It may continue in the background.",
        severity: "warning",
      });
    }
  };

  const handleCancelCall = () => {
    // End the Twilio call
    handleEndCall();
  };

  const handleCloseAlert = () => {
    setAlert({ ...alert, open: false });
  };

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box className="app-container">
        {/* Top Header */}
        <AppBar
          position="static"
          color="transparent"
          elevation={0}
          className="header"
        >
          <Toolbar>
            {(showChatInterface || showCallInterface) && (
              <IconButton
                color="inherit"
                edge="start"
                onClick={handleBackToWelcome}
                sx={{ mr: 2 }}
              >
                <ArrowBackIcon />
              </IconButton>
            )}
            <Typography variant="body1" component="div" className="app-title">
              Customer Web Agent
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <IconButton color="inherit" size="small">
              <GridViewIcon />
            </IconButton>
            <IconButton color="inherit" size="small">
              <NotificationsIcon />
            </IconButton>
            <IconButton color="inherit" size="small">
              <AccountCircleIcon />
            </IconButton>
          </Toolbar>
        </AppBar>

        {!showChatInterface && !showCallInterface ? (
          // Welcome Screen
          <Container className="main-content">
            {/* Welcome Section */}
            <Box className="welcome-container">
              <Avatar className="headset-avatar">
                <HeadsetLogo />
              </Avatar>
              <Typography
                variant="h4"
                component="h1"
                align="center"
                gutterBottom
              >
                Welcome, User
              </Typography>
            </Box>

            {/* Operation Buttons */}
            <Box className="buttons-container">
              <Button
                variant="outlined"
                startIcon={<AirplaneTicketIcon />}
                className="operation-button"
                onClick={() => handleClickOpen("Air ticket operations")}
              >
                Air ticket operations
              </Button>
              <Button
                variant="outlined"
                startIcon={<HotelIcon />}
                className="operation-button"
                onClick={() => handleClickOpen("Hotel Operations")}
              >
                Hotel Operations
              </Button>
            </Box>
          </Container>
        ) : showCallInterface ? (
          // Call Interface Screen
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              height: "calc(100vh - 60px)",
              p: 2,
              width: "100%",
            }}
          >
            <CallInProgress
              phoneNumber="+19098599810"
              callStartTime={callStartTime}
              onCancel={handleCancelCall}
              callStatus={callStatus}
              callSid={callSid}
              onSendText={handleSendLiveText}
              transcripts={transcripts}
            />
            {/* Chat input at bottom */}
            <Box
              sx={{
                p: 2,
                borderTop: "1px solid rgba(255,255,255,0.1)",
                position: "fixed",
                bottom: 0,
                left: 0,
                right: 0,
                bgcolor: "#303030",
              }}
            >
              <TextField
                fullWidth
                variant="outlined"
                placeholder="Type a message..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={handleKeyPress}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <IconButton size="small">
                        <AddCircleOutlineIcon fontSize="small" />
                      </IconButton>
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton size="small">
                        <MicIcon fontSize="small" />
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
                sx={{
                  "& .MuiOutlinedInput-root": {
                    borderRadius: "24px",
                    backgroundColor: "rgba(255,255,255,0.05)",
                    "&:hover fieldset": {
                      borderColor: "rgba(255,255,255,0.23)",
                    },
                  },
                }}
              />
            </Box>
          </Box>
        ) : (
          // Chat Interface Screen
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              height: "calc(100vh - 60px)",
            }}
          >
            {/* Chat Header */}
            <Box sx={{ p: 2, borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
              <Typography variant="h5">Create Order</Typography>
            </Box>

            {/* Chat Messages */}
            <Box sx={{ flexGrow: 1, p: 2, overflow: "auto" }}>
              {messages.map((msg, index) => (
                <ChatMessage
                  key={index}
                  message={msg.text}
                  isUser={msg.isUser}
                />
              ))}
            </Box>

            {/* Action Buttons */}
            <Box
              sx={{ display: "flex", justifyContent: "flex-end", p: 2, gap: 2 }}
            >
              <Button
                variant="outlined"
                onClick={() => {
                  setMessages((prev) => [
                    ...prev,
                    { text: "No, I changed my mind.", isUser: true },
                    {
                      text: "No problem. I won't proceed with the cancellation. Is there anything else you need help with?",
                      isUser: false,
                    },
                  ]);
                }}
              >
                No, I changed my mind
              </Button>
              <Button
                variant="contained"
                onClick={handleProceedCancellation}
                sx={{
                  bgcolor: "white",
                  color: "black",
                  "&:hover": { bgcolor: "#e0e0e0" },
                }}
              >
                Yes, proceed the cancellation
              </Button>
            </Box>

            {/* Chat Input */}
            <Box sx={{ p: 2, borderTop: "1px solid rgba(255,255,255,0.1)" }}>
              <TextField
                fullWidth
                variant="outlined"
                placeholder="Type a message..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={handleKeyPress}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <IconButton size="small">
                        <AddCircleOutlineIcon fontSize="small" />
                      </IconButton>
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton size="small">
                        <MicIcon fontSize="small" />
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
                sx={{
                  "& .MuiOutlinedInput-root": {
                    borderRadius: "24px",
                    backgroundColor: "rgba(255,255,255,0.05)",
                    "&:hover fieldset": {
                      borderColor: "rgba(255,255,255,0.23)",
                    },
                  },
                }}
              />
            </Box>
          </Box>
        )}

        {/* Event Dialog */}
        <Dialog
          open={open}
          onClose={handleClose}
          maxWidth="md"
          PaperProps={{
            style: {
              display: "flex",
              flexDirection: "row",
              borderRadius: "4px",
              overflow: "hidden",
              width: "900px",
              height: "600px",
            },
          }}
        >
          <Box sx={{ flex: 1, display: "flex", flexDirection: "column", p: 0 }}>
            <Box
              sx={{
                p: 2,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
              }}
            >
              <Typography variant="h6">New Event</Typography>
              <IconButton size="small">
                <EditIcon fontSize="small" />
              </IconButton>
            </Box>
            <DialogContent sx={{ p: 0, flex: 1, overflow: "auto" }}>
              <EventForm
                eventType={eventType}
                setEventType={setEventType}
                description={description}
                setDescription={setDescription}
                onFileChange={handleFileChange}
                confirmed={confirmed}
                setConfirmed={setConfirmed}
                additionalInfo={additionalInfo}
                setAdditionalInfo={setAdditionalInfo}
                countryCode={countryCode}
                setCountryCode={setCountryCode}
                phoneNumber={phoneNumber}
                setPhoneNumber={setPhoneNumber}
                userName={userName}
                setUserName={setUserName}
              />
            </DialogContent>
            <DialogActions
              sx={{ p: 2, borderTop: "1px solid rgba(255, 255, 255, 0.1)" }}
            >
              <Button
                onClick={handleCreate}
                fullWidth
                variant="contained"
                sx={{
                  backgroundColor: "white",
                  color: "#333",
                  "&:hover": {
                    backgroundColor: "#e0e0e0",
                  },
                }}
              >
                Create
              </Button>
            </DialogActions>
          </Box>
          <Box
            sx={{
              width: "260px",
              backgroundColor: "#333",
              p: 2,
              display: "flex",
              flexDirection: "column",
              justifyContent: "flex-end",
            }}
          >
            <Typography variant="subtitle2" sx={{ p: 1 }}>
              LLM 1
            </Typography>
          </Box>
        </Dialog>

        {/* Alert Snackbar */}
        <Snackbar
          open={alert.open}
          autoHideDuration={6000}
          onClose={handleCloseAlert}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        >
          <Alert
            onClose={handleCloseAlert}
            severity={alert.severity}
            sx={{ width: "100%" }}
          >
            {alert.message}
          </Alert>
        </Snackbar>
      </Box>
    </ThemeProvider>
  );
}

export default App;
