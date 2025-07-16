import config from './config';

// Code to send https requests to the server
export const sendRequest = async (route, method, body, navigate) => {
  try {
    const userToken = localStorage.getItem('access');
    // if token was none
    let header = null;
    if (
      userToken === null ||
      typeof userToken === 'undefined' ||
      userToken === 'undefined'
    ) {
      header = {
        'Content-Type': 'application/json',
      };
    } else {
      header = {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${userToken}`,
      };
    }
    const response = await fetch(
      `http://localhost:${config.BACKEND_PORT}/${route}`,
      {
        method,
        headers: header,
        body: method !== 'GET' ? JSON.stringify(body) : undefined,
      }
    );

    if (!response.ok) {
      console.error(`The response is ${response}`);
      console.error(`Request failed with status: ${response.status}`);
      throw new Error(`Request failed with status: ${response.status}`);
    }
    return method !== 'DELETE' ? response.json() : {};
  } catch (error) {
    if (error.code === 440) {
      try {
        localStorage.removeItem('access');
        const refresh = localStorage.getItem('refresh');
        const response = await fetch(
          `http://localhost:${config.BACKEND_PORT}/auth/refresh/`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh }),
          }
        );
        if (response.ok) {
          const data = await response.json();
          localStorage.setItem('access', data.token);
          localStorage.setItem('refresh', data.refresh);
          return sendRequest(route, method, body);
        }
      } catch (error) {
        console.error('Failed to refresh token:', error);
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
        if (error.code === 440) {
          navigate('/login');
        }
        throw error;
      }
    }
    alert(`An error occurred: ${error.message}`);
    throw error;
  }
};
