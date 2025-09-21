import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import PortfolioWithAPI from "./components/PortfolioWithAPI";
import AdminDashboard from "./components/AdminDashboard";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PortfolioWithAPI />} />
          <Route path="/case-studies" element={<PortfolioWithAPI />} />
          <Route path="/portfolio" element={<PortfolioWithAPI />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;