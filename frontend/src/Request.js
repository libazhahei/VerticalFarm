import config from './config';

// Improved helper to send HTTP requests and surface validation errors
export const sendRequest = async (route, method, body, navigate) => {
  try {
    // Prepare headers
    const userToken = localStorage.getItem('access');
    const headers = {
      'Content-Type': 'application/json'
    };
    if (userToken && userToken !== 'undefined') {
      headers.Authorization = `Bearer ${userToken}`;
    }

    // Send the request
    const response = await fetch(
      `http://localhost:${config.BACKEND_PORT}/${route}`,
      {
        method,
        headers,
        body: method !== 'GET' ? JSON.stringify(body) : undefined
      }
    );

    // Read raw text and attempt JSON parse
    const text = await response.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }

    // Handle token-refresh status code (e.g., 440)
    if (response.status === 440) {
      // Remove old tokens
      localStorage.removeItem('access');
      localStorage.removeItem('refresh');
      // Attempt refresh
      const refreshToken = localStorage.getItem('refresh');
      if (refreshToken) {
        const refreshRes = await fetch(
          `http://localhost:${config.BACKEND_PORT}/auth/refresh/`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken })
          }
        );
        if (refreshRes.ok) {
          const tokens = await refreshRes.json();
          localStorage.setItem('access', tokens.token);
          localStorage.setItem('refresh', tokens.refresh);
          // Retry original request
          return sendRequest(route, method, body, navigate);
        }
      }
      // If we get here, refresh failed
      if (navigate) navigate('/login');
      throw new Error('Session expired, please login again.');
    }

    // For other non-OK statuses, throw with detailed message
    if (!response.ok) {
      console.error('Request failed:', response.status, data);
      throw new Error(`Request failed (${response.status}): ${JSON.stringify(data)}`);
    }

    // Return JSON or empty for DELETE
    return method !== 'DELETE' ? data : {};
  } catch (error) {
    // Fallback error alert
    alert(`An error occurred: ${error.message}`);
    throw error;
  }
};
