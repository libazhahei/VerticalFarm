import React from 'react';
import { Drawer, List, ListItem, ListItemIcon, ListItemText, Toolbar } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ChatIcon from '@mui/icons-material/Chat';
import SettingsIcon from '@mui/icons-material/Settings';

const drawerWidth = 200;
export default function Sidebar () {
  return (
    <Drawer
      variant="permanent"
      anchor="left"
      PaperProps={{ sx: { width: drawerWidth, bgcolor: 'background.default', color: 'text.primary', borderRight: 'none' } }}
    >
      <Toolbar />
      <List>
        {[
          { text: 'Overview', icon: <HomeIcon /> },
          { text: 'Boards', icon: <DashboardIcon /> },
          { text: 'Messages', icon: <ChatIcon /> },
          { text: 'Settings', icon: <SettingsIcon /> }
        ].map(({ text, icon }) => (
          <ListItem button key={text}>
            <ListItemIcon>{icon}</ListItemIcon>
            <ListItemText primary={text} />
          </ListItem>
        ))}
      </List>
    </Drawer>
  );
}
