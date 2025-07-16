import React, { useState } from 'react';
import { Box, Button, Menu, MenuItem, Typography } from '@mui/material';
import ArrowDropDownIcon from '@mui/icons-material/ArrowDropDown';
import { useNavigate } from 'react-router-dom';
import HighlightOffIcon from '@mui/icons-material/HighlightOff';
import ModeEditIcon from '@mui/icons-material/ModeEdit';

/**
 * Renders an option menu component.
 * @param {Object} props - The component props.
 * @param {Object} props.booking - The booking object.
 * @param {string} props.type - The type of the booking.
 * @param {Function} props.handleRemove - The function to handle removing a booking.
 * @returns {JSX.Element} The rendered OptionMenu component.
 */
function OptionMenu ({ booking, type, handleRemove }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const navigate = useNavigate();

  // check whether the type was current
  const isCurrent = type === 'current';

  /**
   * Handles the click event of the button.
   * @param {Object} event - The click event object.
   */
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  /**
   * Handles the close event of the menu.
   */
  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        borderRadius: '20px',
        marginRight: 2,
      }}
    >
      <Button
        aria-controls={open ? 'options-menu' : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        onClick={handleClick}
        sx={{
          borderRadius: '20px',
          border: '2px solid green',
          color: 'green',
          minWidth: '120px',
          height: '40px',
          textTransform: 'none', // Prevent uppercase text
          marginRight: '8px',
          marginBottom: '10px',
          '& .MuiButton-endIcon': {
            margin: 0,
          },
        }}
        endIcon={<ArrowDropDownIcon />}
      >
        Options
      </Button>
      <Menu
        id="menu-appbar"
        anchorEl={anchorEl}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        keepMounted
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        open={open}
        onClose={handleClose}
      >
        <MenuItem
          onClick={() => navigate(`/ModifyBooking/${booking.uid}/${type}`)}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ModeEditIcon />
            <Typography>Modify Booking</Typography>
          </Box>
        </MenuItem>

        {!isCurrent && (
          <MenuItem
            onClick={() => {
              handleClose();
              handleRemove(booking.uid);
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <HighlightOffIcon />
              <Typography>Remove Listing</Typography>
            </Box>
          </MenuItem>
        )}
      </Menu>
    </Box>
  );
}

export default OptionMenu;
