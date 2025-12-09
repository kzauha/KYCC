import { useEffect, useState } from "react";
import api from "../api/client";

export default function PartyList() {
  const [parties, setParties] = useState([]);

  useEffect(() => {
    api.get("/parties")
      .then(res => setParties(res.data))
      .catch(err => console.log(err));
  }, []);

  return (
    <div style={{ padding: "20px" }}>
      <h1>Party List</h1>

      {parties.length === 0 ? (
        <p>No parties found</p>
      ) : (
        parties.map(p => (
          <div key={p.id} style={{ border: "1px solid #ccc", padding: "10px", margin: "10px 0" }}>
            <h3>{p.name}</h3>
            <p>Type: {p.type}</p>
          </div>
        ))
      )}
    </div>
  );
}
