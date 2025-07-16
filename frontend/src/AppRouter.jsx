import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Dashboard from './page/Dashboard';
const AppRouter = () => {
  return (
    <Routes>
      <Route path="/" element={<Dashboard/>} />
    </Routes>
  );
};

export default AppRouter;
