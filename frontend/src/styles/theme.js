import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#111111',
      light: '#2a2a2a',
      dark: '#080808',
    },
    secondary: {
      main: '#c9a84c',
      light: '#e0c97a',
      dark: '#a8893a',
    },
    background: {
      default: '#FDFBF5',
      paper: '#FBF7EA',
    },
    text: {
      primary: '#1a1a1a',
      secondary: '#4a4a4a',
    },
  },
  typography: {
    fontFamily: 'Inter, "Segoe UI", sans-serif',
    h1: {
      fontWeight: 700,
      color: '#111111',
    },
    h2: {
      fontWeight: 600,
      color: '#111111',
    },
    h3: {
      fontWeight: 600,
      color: '#111111',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          textTransform: 'none',
          fontWeight: 600,
        },
        containedPrimary: {
          backgroundColor: '#111111',
          '&:hover': {
            backgroundColor: '#000000',
          },
        },
        containedSecondary: {
          backgroundColor: '#c9a84c',
          color: '#111111',
          '&:hover': {
            backgroundColor: '#a8893a',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 4px 14px rgba(17,17,17,0.06)',
          border: '1px solid rgba(201,168,76,0.12)',
        },
      },
    },
  },
});

export default theme;