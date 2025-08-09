import React from 'react';
import { Drawer, List, ListItem, ListItemIcon, ListItemText, Toolbar } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import ChatIcon from '@mui/icons-material/Chat';
import { useNavigate } from 'react-router-dom';

const drawerWidth = 200;
export default function Sidebar () {
  const navigate = useNavigate();
  return (
    <Drawer
      variant="permanent"
      anchor="left"
      PaperProps={{ sx: { width: drawerWidth, bgcolor: 'background.default', color: 'text.primary', borderRight: 'none' } }}
    >
      <Toolbar />
      <List>
        {[
          { text: 'Overview', icon: <HomeIcon />, path: '/' },
          { text: 'Report', icon: <ChatIcon />, path: '/report' }
        ].map(({ text, icon, path }) => (
          <ListItem button key={text} onClick={path ? () => navigate(path) : undefined}>
            <ListItemIcon>{icon}</ListItemIcon>
            <ListItemText primary={text} />
          </ListItem>
        ))}
      </List>
    </Drawer>
  );
}
