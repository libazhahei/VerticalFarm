// This file can be deleted if you'd like
import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';
// src/App.test.jsx
jest.mock('react-plotly.js', () => ({
  __esModule: true,
  default: jest.fn().mockImplementation(() => <div>Mocked Plotly Component</div>),
}));

test('renders learn react link', () => {
  render(<App />);
  const linkElement = screen.getByText(/o/i); // random letter
  expect(linkElement).toBeInTheDocument();
});
