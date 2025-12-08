from app.db.database import SessionLocal
from app.db.crud import (
    create_party,
    get_party,
    get_parties,
    get_party_by_tax_id,
    update_party,
    delete_party,
)
from app.schemas.schemas import PartyCreate


def prompt_create(db):
    print("-- Create Party --")
    name = input("Name: ")
    party_type = input("Party type (supplier/manufacturer/distributor/retailer/customer): ")
    tax_id = input("Tax ID (unique): ")
    kyc = input("KYC verified (0-100): ")
    try:
        kyc_val = int(kyc)
    except Exception:
        kyc_val = 0
    party = PartyCreate(name=name, party_type=party_type, tax_id=tax_id, kyc_verified=kyc_val)
    existing = get_party_by_tax_id(db, tax_id)
    if existing:
        print(f"Party with tax_id {tax_id} already exists: id={existing.id} name={existing.name}")
        return
    created = create_party(db, party)
    print(f"Created party id={created.id} name={created.name}")


def prompt_read(db):
    print("-- Read Party --")
    mode = input("Read by (1) id or (2) tax_id ? ")
    if mode.strip() == "1":
        pid = input("Party id: ")
        try:
            pid = int(pid)
        except Exception:
            print("Invalid id")
            return
        p = get_party(db, pid)
        if not p:
            print("Not found")
        else:
            print(p.id, p.name, p.party_type, p.tax_id, p.kyc_verified)
    else:
        tax = input("Tax id: ")
        p = get_party_by_tax_id(db, tax)
        if not p:
            print("Not found")
        else:
            print(p.id, p.name, p.party_type, p.tax_id, p.kyc_verified)


def prompt_update(db):
    print("-- Update Party --")
    pid = input("Party id to update: ")
    try:
        pid = int(pid)
    except Exception:
        print("Invalid id")
        return
    p = get_party(db, pid)
    if not p:
        print("Party not found")
        return
    print(f"Current: {p.id} {p.name} {p.party_type} {p.tax_id} kyc={p.kyc_verified}")
    name = input(f"New name (leave blank to keep '{p.name}'): ")
    party_type = input(f"New party_type (leave blank to keep '{p.party_type}'): ")
    tax_id = input(f"New tax_id (leave blank to keep '{p.tax_id}'): ")
    kyc = input(f"New kyc_verified (leave blank to keep '{p.kyc_verified}'): ")

    updates = {}
    if name.strip():
        updates['name'] = name.strip()
    if party_type.strip():
        updates['party_type'] = party_type.strip()
    if tax_id.strip():
        updates['tax_id'] = tax_id.strip()
    if kyc.strip():
        try:
            updates['kyc_verified'] = int(kyc.strip())
        except Exception:
            pass

    if not updates:
        print("Nothing to update")
        return

    updated = update_party(db, pid, updates)
    if updated:
        print("Updated:", updated.id, updated.name, updated.party_type, updated.tax_id, updated.kyc_verified)
    else:
        print("Update failed")


def prompt_delete(db):
    print("-- Delete Party --")
    pid = input("Party id to delete: ")
    try:
        pid = int(pid)
    except Exception:
        print("Invalid id")
        return
    confirmed = input(f"Are you sure you want to delete party id={pid}? Type 'yes' to confirm: ")
    if confirmed.strip().lower() != 'yes':
        print("Aborted")
        return
    ok = delete_party(db, pid)
    if ok:
        print("Deleted")
    else:
        print("Not found")


def main():
    db = SessionLocal()
    try:
        print("Simple CRUD CLI — Parties")
        print("Options: [c]reate, [r]ead, [u]pdate, [d]elete, [l]ist, [q]uit")
        while True:
            cmd = input("Enter command: ").strip().lower()
            if cmd in ('c', 'create'):
                prompt_create(db)
            elif cmd in ('r', 'read'):
                prompt_read(db)
            elif cmd in ('u', 'update'):
                prompt_update(db)
            elif cmd in ('d', 'delete'):
                prompt_delete(db)
            elif cmd in ('l', 'list'):
                items = get_parties(db)
                for it in items:
                    print(it.id, it.name, it.party_type, it.tax_id, it.kyc_verified)
            elif cmd in ('q', 'quit'):
                print("Thankyou")
                break
            else:
                print("Unknown command — use c/r/u/d/l/q")
    finally:
        db.close()


if __name__ == '__main__':
    main()
