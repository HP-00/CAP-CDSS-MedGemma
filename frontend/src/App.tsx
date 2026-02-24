import { Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence } from "motion/react";
import { Header } from "@/components/layout/header";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { ModeProvider } from "@/stores/mode-store";
import { BatchProvider } from "@/stores/batch-store";
import { PatientsPage } from "@/pages/patients-page";
import { AnalysisPage } from "@/pages/analysis-page";
import { PatientDetailPage } from "@/pages/patient-detail-page";

function App() {
  const location = useLocation();

  return (
    <ModeProvider>
      <BatchProvider>
        <div className="flex h-screen overflow-hidden">
          <AppSidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <Header />
            <main className="flex-1 flex flex-col min-h-0">
              <AnimatePresence mode="wait">
                <Routes location={location} key={location.pathname}>
                  <Route path="/" element={<PatientsPage />} />
                  <Route path="/analysis" element={<AnalysisPage />} />
                  <Route path="/patient/:caseId" element={<PatientDetailPage />} />
                </Routes>
              </AnimatePresence>
            </main>
          </div>
        </div>
      </BatchProvider>
    </ModeProvider>
  );
}

export default App;
