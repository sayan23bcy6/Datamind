import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { LandingPage } from "./pages/LandingPage";
import { DatasetsPage } from "./pages/DatasetsPage";
import { DatasetDetailPage } from "./pages/DatasetDetailPage";
import { InvestigationPage } from "./pages/InvestigationPage";
import { ReviewsPage } from "./pages/ReviewsPage";
import { WatchesPage } from "./pages/WatchesPage";

export const App: React.FC = () => {
  // Theme defaults to the system preference and is held in React state. Do NOT use localStorage.
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return true;
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [darkMode]);

  return (
    <Router>
      <div className={`min-h-screen ${darkMode ? "dark" : ""}`}>
        <div className="min-h-screen bg-slate-950 text-slate-100 dark:bg-slate-950 dark:text-slate-100 transition-colors duration-200">
          <Navbar darkMode={darkMode} setDarkMode={setDarkMode} />
          <main className="pb-16">
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/datasets" element={<DatasetsPage />} />
              <Route path="/datasets/:datasetId" element={<DatasetDetailPage />} />
              <Route path="/investigations/:id" element={<InvestigationPage />} />
              <Route path="/reviews" element={<ReviewsPage />} />
              <Route path="/watches" element={<WatchesPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
};

export default App;
