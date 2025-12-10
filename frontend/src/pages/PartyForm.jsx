import { useState } from "react";
import apiClient from "../api/client";

export default function PartyForm({ onClose, onSuccess }) {
  const [form, setForm] = useState({
    name: "",
    type: "",
    taxId: "",
    country: "",
  });

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setStatus(null);

    try {
      await apiClient.post("/parties", {
        name: form.name,
        type: form.type,
        tax_id: form.taxId,
        country: form.country,
      });

      setStatus("success");

      setTimeout(() => {
        onSuccess();   // ✅ refresh party list
        onClose();    // ✅ close modal
      }, 800);
    } catch (err) {
      console.error(err);
      setStatus("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal fade show d-block" tabIndex="-1">
      <div className="modal-dialog modal-dialog-centered modal-lg">
        <div className="modal-content border-0 rounded-4 shadow">

          {/* ✅ MODAL HEADER */}
          <div className="modal-header">
            <h5 className="modal-title fw-bold">Create New Party</h5>
            <button className="btn-close" onClick={onClose}></button>
          </div>

          {/* ✅ MODAL BODY */}
          <div className="modal-body">
            <form onSubmit={handleSubmit} className="row g-3">

              <div className="col-12">
                <label className="form-label fw-semibold">Party Name</label>
                <input
                  type="text"
                  className="form-control"
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="col-md-6">
                <label className="form-label fw-semibold">Party Type</label>
                <select
                  className="form-select"
                  name="type"
                  value={form.type}
                  onChange={handleChange}
                  required
                >
                  <option value="">Select type</option>
                  <option value="customer">Customer</option>
                  <option value="supplier">Supplier</option>
                  <option value="bank">Bank</option>
                  <option value="partner">Partner</option>
                </select>
              </div>

              <div className="col-md-6">
                <label className="form-label fw-semibold">Tax ID / PAN</label>
                <input
                  type="text"
                  className="form-control"
                  name="taxId"
                  value={form.taxId}
                  onChange={handleChange}
                />
              </div>

              <div className="col-12">
                <label className="form-label fw-semibold">Country</label>
                <input
                  type="text"
                  className="form-control"
                  name="country"
                  value={form.country}
                  onChange={handleChange}
                />
              </div>

              <div className="col-12 d-flex justify-content-end gap-2 pt-3">
                <button type="button" onClick={onClose} className="btn btn-light">
                  Cancel
                </button>

                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? "Saving..." : "Save Party"}
                </button>
              </div>

            </form>

            {status === "success" && (
              <div className="alert alert-success mt-3">✅ Party created successfully</div>
            )}

            {status === "error" && (
              <div className="alert alert-danger mt-3">❌ Failed to create party</div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
