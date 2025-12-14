import apiClient from "./client";

/**
 * Fetch transactions for a given party
 * Backend endpoint:
 * GET /api/parties/{party_id}/transactions
 */
export async function getTransactionsForParty(partyId) {
  const res = await apiClient.get(
    `/api/parties/${partyId}/transactions`
  );
  return res.data;
}
