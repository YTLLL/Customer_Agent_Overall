import React from "react";
import {
  Box,
  Typography,
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  FormControlLabel,
  Checkbox,
  InputAdornment,
  Grid,
} from "@mui/material";
import FileUploadComponent from "../FileUpload/FileUploadComponent";
import "./EventForm.css";

// Country codes data
const countryCodes = [
  { code: "+1", country: "United States/Canada" },
  { code: "+44", country: "United Kingdom" },
  { code: "+61", country: "Australia" },
  { code: "+64", country: "New Zealand" },
  { code: "+49", country: "Germany" },
  { code: "+33", country: "France" },
  { code: "+81", country: "Japan" },
  { code: "+86", country: "China" },
  { code: "+91", country: "India" },
  { code: "+52", country: "Mexico" },
  { code: "+55", country: "Brazil" },
  { code: "+27", country: "South Africa" },
  { code: "+82", country: "South Korea" },
  { code: "+7", country: "Russia" },
  { code: "+971", country: "United Arab Emirates" },
  { code: "+34", country: "Spain" },
  { code: "+39", country: "Italy" },
  { code: "+31", country: "Netherlands" },
  { code: "+46", country: "Sweden" },
  { code: "+65", country: "Singapore" },
];

const EventForm = ({
  eventType,
  setEventType,
  description,
  setDescription,
  onFileChange,
  confirmed,
  setConfirmed,
  additionalInfo,
  setAdditionalInfo,
  countryCode,
  setCountryCode,
  phoneNumber,
  setPhoneNumber,
  userName,
  setUserName,
}) => {
  return (
    <Box
      sx={{
        height: "100%",
        p: 2,
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      <Box className="form-field">
        <Typography variant="caption" className="field-label">
          Event Type *
        </Typography>
        <FormControl fullWidth variant="outlined" size="small">
          <Select
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
          >
            <MenuItem value="Air ticket operations">
              Air ticket operations
            </MenuItem>
            <MenuItem value="Hotel Operations">Hotel Operations</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Box className="form-field">
        <Typography variant="caption" className="field-label">
          {eventType === "Air ticket operations"
            ? "Flight Name *"
            : "Hotel Name *"}
        </Typography>
        <TextField
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          variant="outlined"
          fullWidth
          size="small"
          placeholder={
            eventType === "Air ticket operations"
              ? "Enter flight name/number"
              : "Enter hotel name"
          }
          required
        />
      </Box>

      <Box className="form-field">
        <Typography variant="caption" className="field-label">
          Phone Number *
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={4} sm={3}>
            <FormControl fullWidth variant="outlined" size="small">
              <Select
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value)}
              >
                {countryCodes.map((country) => (
                  <MenuItem key={country.code} value={country.code}>
                    {country.code} {country.country}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={8} sm={9}>
            <TextField
              fullWidth
              variant="outlined"
              size="small"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="Enter phone number"
              required
            />
          </Grid>
        </Grid>
      </Box>

      <Box className="form-field">
        <Typography variant="caption" className="field-label">
          Full Name *
        </Typography>
        <TextField
          value={userName}
          onChange={(e) => setUserName(e.target.value)}
          variant="outlined"
          fullWidth
          size="small"
          placeholder="Enter your full name"
          required
        />
      </Box>

      <Box className="form-field">
        <Typography variant="caption" className="field-label">
          Personal Information
        </Typography>
        <TextField
          multiline
          rows={3}
          value={additionalInfo}
          onChange={(e) => setAdditionalInfo(e.target.value)}
          variant="outlined"
          fullWidth
          size="small"
          placeholder="Enter any additional personal information here..."
        />
      </Box>

      <FileUploadComponent onFileChange={onFileChange} />

      <FormControlLabel
        control={
          <Checkbox
            size="small"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
        }
        label={
          <Typography variant="caption">
            Please Confirm: By uploading, you authorize the use of your data for
            this feature. We take data security seriously, but you acknowledge
            the inherent risks once data is uploaded.
          </Typography>
        }
        sx={{ mt: 1 }}
      />
    </Box>
  );
};

export default EventForm;
