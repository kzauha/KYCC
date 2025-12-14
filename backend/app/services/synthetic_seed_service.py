from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models import models
from app.config.synthetic_mapping import get_default_mapping


class SeedIngestError(Exception):
    pass


def load_seed_file(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise SeedIngestError(f"Seed file not found: {p}")
    try:
        return json.loads(p.read_text())
    except Exception as exc:
        raise SeedIngestError(f"Failed to parse seed file {p}: {exc}") from exc


def _map_txn_type(raw: str, mapping: Dict[str, str]) -> str:
    return mapping.get(raw.lower(), raw.lower())


def _map_rel_type(raw: str, mapping: Dict[str, str]) -> str:
    return mapping.get(raw.lower(), raw.lower())


def _map_party_type(profile: str, mapping: Dict[str, str], provided: str | None) -> str:
    if provided:
        return provided.lower()
    return mapping.get(profile, "customer")


def ingest_seed_payload(
    db: Session,
    payload: Dict[str, Any],
    batch_id: str,
    overwrite: bool = False,
    mapping_config=None,
) -> Dict[str, int]:
    """Ingest synthetic seed payload into Parties/Accounts/Transactions/Relationships.

    Idempotency: default skip existing parties by external_id; if overwrite=True, delete and replace
    rows for the batch.
    """
    if payload.get("batch_id") != batch_id:
        raise SeedIngestError("batch_id mismatch between payload and request")

    mapping = mapping_config or get_default_mapping()
    txn_map = {k.lower(): v for k, v in mapping.transaction_type_map.items()}
    rel_map = {k.lower(): v for k, v in mapping.relationship_type_map.items()}
    profile_party_map = mapping.profile_party_type_default

    parties_raw: List[Dict[str, Any]] = payload.get("parties", [])
    accounts_raw: List[Dict[str, Any]] = payload.get("accounts", [])
    transactions_raw: List[Dict[str, Any]] = payload.get("transactions", [])
    relationships_raw: List[Dict[str, Any]] = payload.get("relationships", [])

    # First pass: ensure parties exist / are created
    ext_to_party: Dict[str, models.Party] = {}

    # Overwrite handling: remove existing rows for external_id when overwrite=True
    for p in parties_raw:
        ext_id = p.get("party_id")
        if not ext_id:
            continue
        existing = db.query(models.Party).filter(models.Party.external_id == ext_id).first()
        if existing:
            if overwrite:
                # Delete related rows tied to this party (accounts, txns, relationships)
                db.query(models.Transaction).filter(models.Transaction.party_id == existing.id).delete()
                db.query(models.Transaction).filter(models.Transaction.counterparty_id == existing.id).delete()
                db.query(models.Account).filter(models.Account.party_id == existing.id).delete()
                db.query(models.Relationship).filter(
                    (models.Relationship.from_party_id == existing.id)
                    | (models.Relationship.to_party_id == existing.id)
                ).delete()
                db.query(models.GroundTruthLabel).filter(models.GroundTruthLabel.party_id == existing.id).delete()
                db.delete(existing)
                db.flush()  # ensure deletions are applied before re-insert
            else:
                ext_to_party[ext_id] = existing

    # Create missing parties
    for p in parties_raw:
        ext_id = p.get("party_id")
        if not ext_id or ext_id in ext_to_party:
            continue
        profile = p.get("profile", "normal")
        party_type_raw = _map_party_type(profile, profile_party_map, p.get("party_type"))
        allowed_db_party_types = {"SUPPLIER", "MANUFACTURER", "DISTRIBUTOR", "RETAILER", "CUSTOMER"}
        try:
            party_type = models.PartyType(party_type_raw.lower())
            candidate = party_type.name  # enum name (uppercase)
            party_type_db_value = candidate if candidate in allowed_db_party_types else "CUSTOMER"
        except Exception:
            party_type_db_value = "CUSTOMER"
        party = models.Party(
            external_id=ext_id,
            batch_id=batch_id,
            name=p.get("name", ext_id),
            party_type=party_type_db_value,
            kyc_verified=p.get("kyc_verified", 0),
            tax_id=p.get("tax_id"),
            registration_number=p.get("registration_number"),
            address=p.get("address"),
            contact_person=p.get("contact_person"),
            email=p.get("email"),
            phone=p.get("phone"),
        )
        db.add(party)
        db.flush()
        ext_to_party[ext_id] = party

        # Create ground truth label from synthetic profile
        try:
            risk_map = {
                "poor": ("high", 1),
                "fair": ("medium", 0),
                "good": ("low", 0),
                "excellent": ("low", 0),
            }
            risk_level, will_default = risk_map.get(profile.lower(), ("low", 0))
            lbl = models.GroundTruthLabel(
                party_id=party.id,
                will_default=will_default,
                risk_level=risk_level,
                label_source="synthetic",
                label_confidence=1.0,
                reason=f"Derived from synthetic profile '{profile}'",
                dataset_batch=batch_id,
            )
            db.add(lbl)
            db.flush()
        except Exception:
            # Non-fatal: continue ingest without label
            pass

    # Create accounts
    ext_acct_to_db: Dict[str, models.Account] = {}
    for acc in accounts_raw:
        ext_acc_id = acc.get("account_id") or acc.get("account_number")
        party_ext = acc.get("party_id")
        if not ext_acc_id or party_ext not in ext_to_party:
            continue
        party = ext_to_party[party_ext]
        account = models.Account(
            external_id=ext_acc_id,
            batch_id=batch_id,
            party_id=party.id,
            account_number=acc.get("account_number", ext_acc_id),
            account_type=acc.get("account_type", "checking"),
            currency=acc.get("currency", "USD"),
            balance=acc.get("balance", 0.0),
        )
        db.add(account)
        db.flush()
        ext_acct_to_db[ext_acc_id] = account

    # Create transactions
    txn_count = 0
    for txn in transactions_raw:
        party_ext = txn.get("party_id")
        counter_ext = txn.get("counterparty_id")
        if party_ext not in ext_to_party or (counter_ext and counter_ext not in ext_to_party):
            continue
        account_ext = txn.get("account_id") or txn.get("account")
        account = ext_acct_to_db.get(account_ext)
        txn_type_raw = _map_txn_type(txn.get("txn_type") or txn.get("transaction_type") or "payment", txn_map)
        try:
            txn_type = models.TransactionType(txn_type_raw)
        except Exception:
            txn_type = models.TransactionType.PAYMENT
        t = models.Transaction(
            batch_id=batch_id,
            party_id=ext_to_party[party_ext].id,
            counterparty_id=ext_to_party[counter_ext].id if counter_ext else None,
            account_id=account.id if account else None,
            transaction_date=datetime_from_iso(txn.get("ts") or txn.get("transaction_date")),
            amount=txn.get("amount", 0.0),
            transaction_type=txn_type,
            reference=txn.get("reference"),
        )
        db.add(t)
        txn_count += 1

    # Create relationships
    rel_count = 0
    for rel in relationships_raw:
        from_ext = rel.get("from_party_id")
        to_ext = rel.get("to_party_id")
        if from_ext not in ext_to_party or to_ext not in ext_to_party:
            continue
        rel_type_raw = _map_rel_type(rel.get("relationship_type", "sells_to"), rel_map)
        try:
            rel_type = models.RelationshipType(rel_type_raw)
        except Exception:
            rel_type = models.RelationshipType.SELLS_TO
        r = models.Relationship(
            batch_id=batch_id,
            from_party_id=ext_to_party[from_ext].id,
            to_party_id=ext_to_party[to_ext].id,
            relationship_type=rel_type,
            established_date=datetime_from_iso(rel.get("established_date")),
        )
        db.add(r)
        rel_count += 1

    db.commit()
    return {
        "parties": len(ext_to_party),
        "accounts": len(ext_acct_to_db),
        "transactions": txn_count,
        "relationships": rel_count,
    }


def ingest_seed_file(db: Session, file_path: str | Path, batch_id: str, overwrite: bool = False) -> Dict[str, int]:
    payload = load_seed_file(file_path)
    return ingest_seed_payload(db=db, payload=payload, batch_id=batch_id, overwrite=overwrite)


def datetime_from_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
