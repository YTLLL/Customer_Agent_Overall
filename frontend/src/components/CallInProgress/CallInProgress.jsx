import React, { useState, useEffect } from "react";
import { Box, Typography, Paper, Avatar, Button } from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import HeadsetLogo from "../HeadsetLogo/HeadsetLogo"; // Make sure to import or define this

// Component to display when a call is in progress
const CallInProgress = ({ phoneNumber, callStartTime, onCancel }) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [callStatus, setCallStatus] = useState(
    "Explaining the reasons of cancellation..."
  );

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

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", p: 2, maxWidth: "400px" }}
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
              Calling {phoneNumber} customer support
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
    </Box>
  );
};
