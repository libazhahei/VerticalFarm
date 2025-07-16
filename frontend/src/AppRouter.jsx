import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Dashboard from './page/Dashboard';
import DevicePage from './page/Device';
const AppRouter = () => {
  return (
    <Routes>
      <Route path="/" element={<Dashboard/>} />
      <Route path="/device" element={<DevicePage/>} />
    </Routes>
  );
};

export default AppRouter;
