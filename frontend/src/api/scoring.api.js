import apiClient from "./client";

/**
 * Scoring API
 * Backend prefix: /api/scoring
 */

/**
 * Compute credit score (command)
 * POST /api/scoring/score/{party_id}
 * Optional query params:
 * - model_version
 * - include_explanation (default true)
 */
export async function computeCreditScore(
  partyId,
  { modelVersion = null, includeExplanation = true } = {}
) {
  const params = {};
  if (modelVersion) params.model_version = modelVersion;
  params.include_explanation = includeExplanation;

  const res = await apiClient.post(`/api/scoring/score/${partyId}`, null, {
    params,
  });

  return res.data;
}

/**
 * Get score history (read)
 * GET /api/scoring/score/{party_id}/history?limit=10
 */
export async function getScoreHistory(partyId, limit = 10) {
  const res = await apiClient.get(`/api/scoring/score/${partyId}/history`, {
    params: { limit },
  });
  return res.data;
}

/**
 * Get features used for scoring (read)
 * GET /api/scoring/features/{party_id}
 */
export async function getPartyFeatures(partyId) {
  const res = await apiClient.get(`/api/scoring/features/${partyId}`);
  return res.data;
}

/**
 * Compute features (command)
 * POST /api/scoring/compute-features/{party_id}
 */
export async function computeFeaturesForParty(partyId) {
  const res = await apiClient.post(`/api/scoring/compute-features/${partyId}`);
  return res.data;
}
