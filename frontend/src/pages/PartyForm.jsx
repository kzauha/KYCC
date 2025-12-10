import { useState } from "react";
import apiClient from "../api/client";

export default function PartyForm({ onClose, onSuccess }) {
  const [form, setForm] = useState({
    name: "",
    party_type: "",
    tax_id: "",
    registration_number: "",
    address: "",
    contact_person: "",
    email: "",
    phone: "",
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
      await apiClient.post("/api/parties/", {
        name: form.name,
        party_type: form.party_type,              // ✅ EXACT BACKEND FIELD
        tax_id: form.tax_id || null,
        registration_number: form.registration_number || null,
        address: form.address || null,
        contact_person: form.contact_person || null,
        email: form.email || null,
        phone: form.phone || null,
        kyc_verified: 0                            // ✅ REQUIRED BY BACKEND
      });

      setStatus("success");

      setTimeout(() => {
        onSuccess();   // refresh party list
        onClose();     // close modal
      }, 800);

    } catch (err) {
      console.error(err);
      setStatus("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal fade show d-block">
      <div className="modal-dialog modal-dialog-centered modal-lg">
        <div className="modal-content border-0 rounded-4 shadow">
          <div className="modal-header">
            <h5 className="modal-title fw-bold">Create New Party</h5>
            <button className="btn-close" onClick={onClose}></button>
          </div>

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
                  name="party_type"
                  value={form.party_type}
                  onChange={handleChange}
                  required
                >
                  <option value="">Select type</option>
                  {/* ✅ MUST MATCH PartyType ENUM EXACTLY */}
                  <option value="supplier">Supplier</option>
                  <option value="manufacturer">Manufacturer</option>
                  <option value="distributor">Distributor</option>
                  <option value="retailer">Retailer</option>
                  <option value="customer">Customer</option>
                  <option value="bank">Bank</option>
                  <option value="partner">Partner</option>
                </select>
              </div>

              <div className="col-md-6">
                <label className="form-label fw-semibold">Tax ID</label>
                <input
                  type="text"
                  className="form-control"
                  name="tax_id"
                  value={form.tax_id}
                  onChange={handleChange}
                />
              </div>

              <div className="col-md-6">
                <label className="form-label fw-semibold">Registration Number</label>
                <input
                  type="text"
                  className="form-control"
                  name="registration_number"
                  value={form.registration_number}
                  onChange={handleChange}
                />
              </div>

              <div className="col-md-6">
                <label className="form-label fw-semibold">Contact Person</label>
                <input
                  type="text"
                  className="form-control"
                  name="contact_person"
                  value={form.contact_person}
                  onChange={handleChange}
                />
              </div>

              <div className="col-12">
                <label className="form-label fw-semibold">Address</label>
                <input
                  type="text"
                  className="form-control"
                  name="address"
                  value={form.address}
                  onChange={handleChange}
                />
              </div>

              <div className="col-md-6">
                <label className="form-label fw-semibold">Email</label>
                <input
                  type="email"
                  className="form-control"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                />
              </div>

              <div className="col-md-6">
                <label className="form-label fw-semibold">Phone</label>
                <input
                  type="text"
                  className="form-control"
                  name="phone"
                  value={form.phone}
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
