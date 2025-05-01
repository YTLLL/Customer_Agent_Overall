import React from "react";
import { Box, Button } from "@mui/material";
import AirplaneTicketIcon from "@mui/icons-material/AirplaneTicket";
import HotelIcon from "@mui/icons-material/Hotel";
import "./OperationButtons.css";

const OperationButtons = () => {
  return (
    <Box className="buttons-container">
      <Button
        variant="outlined"
        startIcon={<AirplaneTicketIcon />}
        className="operation-button"
      >
        Air ticket operations
      </Button>
      <Button
        variant="outlined"
        startIcon={<HotelIcon />}
        className="operation-button"
      >
        Hotel Operations
      </Button>
    </Box>
  );
};

export default OperationButtons;
