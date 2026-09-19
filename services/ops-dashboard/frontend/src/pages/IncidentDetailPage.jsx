import React from 'react';
import { Container, Typography, Button, Box, AppBar, Toolbar } from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowBack } from '@mui/icons-material';

function IncidentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  return (
    <Box>
      <AppBar position="static">
        <Toolbar>
          <Button color="inherit" startIcon={<ArrowBack />} onClick={() => navigate('/')}>
            Back
          </Button>
          <Typography variant="h6" sx={{ ml: 2 }}>
            Incident Details: {id}
          </Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Typography variant="body1">
          Detailed view for incident {id} (Coming soon...)
        </Typography>
      </Container>
    </Box>
  );
}

export default IncidentDetailPage;
