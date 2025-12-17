import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api/client";
import CreditScoreView from "./CreditScore";
import NetworkGraphView from "./NetworkGraph";
import TransactionList from "../components/transactions/TransactionList";

export default function PartyDetail() {
    const { id } = useParams();
    const [party, setParty] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchParty();
    }, [id]);

    const fetchParty = async () => {
        try {
            setLoading(true);
            // Try to fetch specific party. If backend doesn't support it, we might need to fetch all and find.
            // Based on previous files, let's try direct fetch or fetch all.
            // Assuming standard REST for now, if fails we fix.
            const res = await api.get(`/api/parties/${id}`);
            setParty(res.data);
        } catch (err) {
            console.error("Failed to load party", err);
            // Fallback: If /api/parties/:id doesn't exist, maybe fetch all (less efficient but works for MVP)
            try {
                const allRes = await api.get("/api/parties/");
                const found = allRes.data.find(p => String(p.id) === String(id));
                if (found) setParty(found);
            } catch (e) {
                console.error("Fallback fetch failed", e);
            }
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="text-center py-5">Loading party details...</div>;
    if (!party) return <div className="text-center py-5 text-danger">Party not found</div>;

    return (
        <div className="container-fluid py-4">
            {/* HEADER */}
            <div className="mb-4">
                <Link to="/" className="text-decoration-none text-secondary mb-2 d-inline-block">
                    <i className="bi bi-arrow-left me-1"></i> Back to List
                </Link>
                <div className="d-flex justify-content-between align-items-end">
                    <div>
                        <h2 className="fw-bold mb-0">{party.name}</h2>
                        <div className="text-muted d-flex gap-3 align-items-center mt-1">
                            <span className="badge bg-primary-subtle text-primary border border-primary-subtle">
                                {party.party_type}
                            </span>
                            <span><i className="bi bi-hash me-1"></i> ID: {party.id}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div className="row g-4">

                {/* LEFT COLUMN: CREDIT & TRANSACTIONS */}
                <div className="col-lg-8 d-flex flex-column gap-5">

                    {/* CREDIT SCORE SECTION */}
                    <section>
                        <h4 className="fw-bold mb-3 border-bottom pb-2">Credit Score</h4>
                        <CreditScoreView party={party} />
                    </section>

                    {/* TRANSACTIONS SECTION */}
                    <section>
                        <h4 className="fw-bold mb-3 border-bottom pb-2">Transaction History</h4>
                        <div className="card border-0 shadow-sm rounded-4 p-4">
                            <TransactionList partyId={party.id} />
                        </div>
                    </section>

                </div>

                {/* RIGHT COLUMN: NETWORK GRAPH (Vertical) */}
                <div className="col-lg-4">
                    <section className="h-100 d-flex flex-column">
                        <h4 className="fw-bold mb-3 border-bottom pb-2">Network Graph</h4>
                        <div className="flex-grow-1" style={{ minHeight: "800px" }}>
                            <NetworkGraphView party={party} />
                        </div>
                    </section>
                </div>

            </div>
        </div>
    );
}
