import { useEffect, useState } from "react";
import api from "../api/client";

export default function RelationshipForm() {
  const [parties, setParties] = useState([]);
  const [form, setForm] = useState({
    fromParty: "",
    toParty: "",
    type: "",
  });

  const [status, setStatus] = useState("");

  useEffect(() => {
    api.get("/parties")
      .then(res => setParties(res.data))
      .catch(err => console.error(err));
  }, []);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("Saving...");

    try {
      await api.post("/relationships", {
        from_party_id: form.fromParty,
        to_party_id: form.toParty,
        type: form.type,
      });

      setStatus("Relationship added successfully ✔");
    } catch (err) {
      console.error(err);
      setStatus("Error creating relationship ❌");
    }
  }

  return (
    <div style={{ padding: 20 }}>
      <h1>Create Relationship</h1>

      <form onSubmit={handleSubmit}>
        <label>
          From Party:
          <select name="fromParty" value={form.fromParty} onChange={handleChange} required>
            <option value="">Select</option>
            {parties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </label>
        <br /><br />

        <label>
          To Party:
          <select name="toParty" value={form.toParty} onChange={handleChange} required>
            <option value="">Select</option>
            {parties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </label>
        <br /><br />

        <label>
          Relationship Type:
          <select name="type" value={form.type} onChange={handleChange} required>
            <option value="">Select</option>
            <option value="supplier">Supplier</option>
            <option value="customer">Customer</option>
            <option value="partner">Partner</option>
          </select>
        </label>

        <br /><br />
        <button type="submit">Save Relationship</button>
      </form>

      {status && <p>{status}</p>}
    </div>
  );
}
