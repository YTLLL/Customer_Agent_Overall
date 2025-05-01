import React from "react";
import { AppBar, Toolbar, Typography, IconButton } from "@mui/material";
import GridViewIcon from "@mui/icons-material/GridView";
import NotificationsIcon from "@mui/icons-material/Notifications";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import "./Header.css";

const Header = () => {
  return (
    <AppBar
      position="static"
      color="transparent"
      elevation={0}
      className="header"
    >
      <Toolbar>
        <Typography variant="h6" component="div" className="app-title">
          CallingMaster
        </Typography>
        <div className="header-icons">
          <IconButton color="inherit">
            <GridViewIcon />
          </IconButton>
          <IconButton color="inherit">
            <NotificationsIcon />
          </IconButton>
          <IconButton color="inherit">
            <AccountCircleIcon />
          </IconButton>
        </div>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
