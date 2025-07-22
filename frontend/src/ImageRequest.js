import config from './config';
import axios from 'axios';
import { sendRequest } from './Request';

// Code to fetch images from the backend server
export const ImageRequest = async (route, method, body, navigate) => {
  try {
    const userToken = localStorage.getItem('access');
    let header = null;
    if (
      userToken === null ||
      typeof userToken === 'undefined' ||
      userToken === 'undefined'
    ) {
      header = {
        'Content-Type': 'multipart/form-data',
      };
    } else {
      header = {
        'content-type': 'multipart/form-data',
        Authorization: `Bearer ${userToken}`,
      };
    }
    let response = null;
    if (method === 'POST') {
      response = await axios.post(
        `http://localhost:${config.BACKEND_PORT}/${route}`,
        body,
        {
          headers: header,
        }
      );
    } else if (method === 'GET') {
      response = await axios.get(
        `http://localhost:${config.BACKEND_PORT}/${route}`,
        body,
        {
          headers: header,
        }
      );
    }
    if (response.status !== 201) {
      console.error(`The response is ${response}`);
      console.error(`Request failed with status: ${response.status}`);
      throw new Error(`Request failed with status: ${response.status}`);
    }
    return response;
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
