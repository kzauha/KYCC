import { useState } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";   // we made this earlier

export default function PartyForm() {
  const [form, setForm] = useState({
    name: "",
    type: "",
    taxId: "",
    country: "",
  });

  const [status, setStatus] = useState(null); // success / error message
  const navigate = useNavigate();

  function handleChange(e) {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("Saving...");

    try {
      // adjust keys to whatever backend expects later
      await apiClient.post("/parties", {
        name: form.name,
        type: form.type,
        tax_id: form.taxId,
        country: form.country,
      });

      setStatus("Party created successfully ✅");
      // after 1 second go back to list
      setTimeout(() => navigate("/"), 1000);
    } catch (err) {
      console.error(err);
      setStatus("Something went wrong ❌ (backend may not be ready yet)");
    }
  }

  return (
    <div className="page">
      <h1>Create New Party</h1>

      <form className="form" onSubmit={handleSubmit}>
        <label>
          Name
          <input
            name="name"
            value={form.name}
            onChange={handleChange}
            required
          />
        </label>

        <label>
          Type
          <select
            name="type"
            value={form.type}
            onChange={handleChange}
            required
          >
            <option value="">Select type</option>
            <option value="customer">Customer</option>
            <option value="supplier">Supplier</option>
            <option value="bank">Bank</option>
          </select>
        </label>

        <label>
          Tax ID
          <input
            name="taxId"
            value={form.taxId}
            onChange={handleChange}
          />
        </label>

        <label>
          Country
          <input
            name="country"
            value={form.country}
            onChange={handleChange}
          />
        </label>

        <button type="submit">Save Party</button>
      </form>

      {status && <p className="status">{status}</p>}
    </div>
  );
}
