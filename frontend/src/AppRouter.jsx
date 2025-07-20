import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Dashboard from './page/Dashboard';
import ReportPage from './page/Report';
const AppRouter = () => {
  return (
    <Routes>
      <Route path="/" element={<Dashboard/>} />
      <Route path="/report" element={<ReportPage/>} />
    </Routes>
  );
};

export default AppRouter;
