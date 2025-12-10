import { BrowserRouter, Routes, Route } from "react-router-dom";

import Sidebar from "./components/Sidebar";

import PartyList from "./pages/PartyList";
import PartyForm from "./pages/PartyForm";
import RelationshipForm from "./pages/RelationshipForm";
import NetworkGraph from "./pages/NetworkGraph";
import CreditScore from "./pages/CreditScore";
import FileUpload from "./pages/FileUpload";

function App() {
  return (
    <BrowserRouter>
      <div className="d-flex">

        {/* ✅ FIXED SIDEBAR */}
        <Sidebar />

        {/* ✅ MAIN CONTENT AREA */}
        <div
          className="flex-grow-1"
          style={{
            marginLeft: "240px",
            minHeight: "100vh",
            backgroundColor: "#f5f7fa",
          }}
        >
          <div className="container-fluid py-4">
            <Routes>
              <Route path="/" element={<PartyList />} />
              <Route path="/new" element={<PartyForm />} />
              <Route path="/relationship" element={<RelationshipForm />} />
              <Route path="/network" element={<NetworkGraph />} />
              <Route path="/credit" element={<CreditScore />} />
              <Route path="/upload" element={<FileUpload />} />
            </Routes>
          </div>
        </div>

      </div>
    </BrowserRouter>
  );
}

export default App;
