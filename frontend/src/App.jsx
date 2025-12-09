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
      <div style={{ display: "flex" }}>
        
        <Sidebar />

        {/* MAIN CONTENT AREA */}
        <div style={{ marginLeft: "220px", padding: "20px", width: "100%" }}>
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
    </BrowserRouter>
  );
}

export default App;
