import apiClient from "./client";

/**
 * Parties API
 * Backend prefix: /api/parties
 * We use trailing slashes to avoid FastAPI 307 redirects (which can trigger CORS in dev).
 */

export async function getAllParties() {
  const res = await apiClient.get("/api/parties/");
  return res.data;
}

export async function getParty(partyId) {
  const res = await apiClient.get(`/api/parties/${partyId}/`);
  return res.data;
}

export async function createParty(payload) {
  const res = await apiClient.post("/api/parties/", payload);
  return res.data;
}

/**
 * Party credit (party-owned view)
 * GET /api/parties/{party_id}/credit-score
 */
export async function getPartyCreditScore(partyId) {
  const res = await apiClient.get(`/api/parties/${partyId}/credit-score`);
  return res.data;
}
