import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Dashboard from './page/Dashboard';
import DashboardNew from './page/DashboardNew';
const AppRouter = () => {
  return (
    <Routes>
      <Route path="/" element={<Dashboard/>} />
      <Route path="/new" element={<DashboardNew/>} />
    </Routes>
  );
};

export default AppRouter;
