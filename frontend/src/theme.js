import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#00e5ff' },
    secondary: { main: '#d500f9' },
    success: { main: '#4caf50' },
    background: { default: '#0d0d1a', paper: 'rgba(255,255,255,0.05)' },
    text: { primary: '#ffffff', secondary: 'rgba(255,255,255,0.7)' }
  },
  typography: {
    fontSize: 18,
    h4: { fontSize: '3rem', fontWeight: 700 },
    subtitle1: { fontSize: '1.75rem', fontWeight: 600 },
    h6: { fontSize: '1.5rem', fontWeight: 600 },
    body1: { fontSize: '1.125rem', fontWeight: 500 },
    body2: { fontSize: '1rem', fontWeight: 500 },
    caption: { fontSize: '0.95rem', fontWeight: 500 }
  },
  shape: { borderRadius: 8 }
});

export default theme;
