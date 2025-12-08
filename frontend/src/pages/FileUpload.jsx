import React, { useState } from "react";
import apiClient from "../api/client";

export default function FileUpload() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");

  function handleFile(e) {
    setFile(e.target.files[0]);
  }

  async function handleUpload() {
    if (!file) return alert("Please select a CSV file!");

    const formData = new FormData();
    formData.append("file", file);

    try {
      setStatus("Uploading...");
      await apiClient.post("/import/transactions", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setStatus("Upload successful ✅");
    } catch (err) {
      console.error(err);
      setStatus("Upload failed ❌ (backend not ready yet)");
    }
  }

  return (
    <div style={{ padding: "20px" }}>
      <h1>Upload Transactions CSV</h1>

      <input type="file" accept=".csv" onChange={handleFile} />
      <button onClick={handleUpload}>Upload</button>

      {status && <p>{status}</p>}
    </div>
  );
}
