from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from .base import BaseAdapter


class SyntheticAdapter(BaseAdapter):
    """Generates deterministic synthetic payloads that mimic CBS/Bank APIs.

    Output schema:
    {
        "party": {
            "party_id": str,
            "name": str,
            "created_at": iso8601,
        },
        "accounts": [
            {"account_id": str, "type": str, "currency": str, "balance": float}
        ],
        "transactions": [
            {
                "txn_id": str,
                "account_id": str,
                "amount": float,
                "currency": str,
                "ts": iso8601,
                "category": str,
                "counterparty": str,
            }
        ],
        "relationships": [
            {"type": str, "source_party_id": str, "target_party_id": str}
        ],
    }
    """

    source_type = "synthetic"

    def parse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a synthetic payload.

        Accepts optional seed inputs:
        - party_id: str
        - name: str
        - accounts: int (default 2)
        - transactions_per_account: int (default 5)
        - start_days_ago: int (default 30)
        - currency: str (default "USD")
        """

        party_id = str(data.get("party_id", "P-0001"))
        name = str(data.get("name", "Test Party"))
        accounts_n = int(data.get("accounts", 2))
        tx_per_acc = int(data.get("transactions_per_account", 5))
        start_days_ago = int(data.get("start_days_ago", 30))
        currency = str(data.get("currency", "USD"))

        now = datetime.utcnow()
        start = now - timedelta(days=start_days_ago)

        accounts: List[Dict[str, Any]] = []
        transactions: List[Dict[str, Any]] = []

        # Create accounts
        for i in range(accounts_n):
            acc_id = f"A-{party_id}-{i+1:03d}"
            acc_type = "checking" if i % 2 == 0 else "savings"
            balance = round(1000.0 + (i * 523.17), 2)
            accounts.append(
                {
                    "account_id": acc_id,
                    "type": acc_type,
                    "currency": currency,
                    "balance": balance,
                }
            )

            # Create transactions for each account
            for t in range(tx_per_acc):
                sign = -1.0 if t % 3 == 0 else 1.0
                amount = round(sign * (20.0 + (t * 7.5) + i), 2)
                ts = start + timedelta(days=(i * 3 + t))
                transactions.append(
                    {
                        "txn_id": f"T-{acc_id}-{t+1:04d}",
                        "account_id": acc_id,
                        "amount": amount,
                        "currency": currency,
                        "ts": ts.isoformat() + "Z",
                        "category": "payment" if sign < 0 else "deposit",
                        "counterparty": "Merchant X" if sign < 0 else "Employer Y",
                    }
                )

        relationships = [
            {"type": "owns", "source_party_id": party_id, "target_party_id": a["account_id"]}
            for a in accounts
        ]

        payload: Dict[str, Any] = {
            "party": {"party_id": party_id, "name": name, "created_at": now.isoformat() + "Z"},
            "accounts": accounts,
            "transactions": transactions,
            "relationships": relationships,
        }

        return payload
