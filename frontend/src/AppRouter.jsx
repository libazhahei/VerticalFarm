import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Dashboard from './page/Dashboard';
import DevicePage from './page/Device';
import ReportPage from './page/Report';
const AppRouter = () => {
  return (
    <Routes>
      <Route path="/" element={<Dashboard/>} />
      <Route path="/device" element={<DevicePage/>} />
      <Route path="/report" element={<ReportPage/>} />
    </Routes>
  );
};

export default AppRouter;
