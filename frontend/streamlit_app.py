"""Simple Streamlit frontend for the KYCC API.

Usage:
  1. Activate your backend venv and start the API: `uvicorn main:app --reload --port 8000`
  2. Install streamlit and requests in your venv: `pip install streamlit requests`
  3. Run this app from the `backend/` folder:
       streamlit run streamlit_app.py

This app exposes basic functionality present in the backend code:
 - List/create/update/delete Parties
 - List/create/delete Relationships
 - View party network (upstream/downstream) and direct counterparties
 - View stats and health

This is intentionally minimal and uses the public HTTP API endpoints.
"""

import streamlit as st
import requests
from typing import Any, Dict, List

"""Simple Streamlit frontend for the KYCC API.

Usage:
  1. Activate your backend venv and start the API: `uvicorn main:app --reload --port 8000`
  2. Install streamlit and requests in your venv: `pip install streamlit requests`
  3. Run this app from the `frontend/` folder:
       streamlit run streamlit_app.py

This app exposes basic functionality present in the backend code:
 - List/create/update/delete Parties
 - List/create/delete Relationships
 - View party network (upstream/downstream) and direct counterparties
 - View stats and health

This is intentionally minimal and uses the public HTTP API endpoints.
"""

import streamlit as st
import requests
from typing import Any, Dict, List, Tuple


def api_url(base: str, path: str) -> str:
    return base.rstrip("/") + path


def api_get(base: str, path: str, params: Dict[str, Any] = None):
    try:
        r = requests.get(api_url(base, path), params=params, timeout=5)
        return r
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def api_post(base: str, path: str, json_data: Dict[str, Any]):
    try:
        r = requests.post(api_url(base, path), json=json_data, timeout=5)
        return r
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def api_put(base: str, path: str, json_data: Dict[str, Any]):
    try:
        r = requests.put(api_url(base, path), json=json_data, timeout=5)
        return r
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def api_delete(base: str, path: str):
    try:
        r = requests.delete(api_url(base, path), timeout=5)
        return r
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def _normalize_response_json(r) -> Tuple[Any, bool]:
    """Return (data, is_list) where data is the parsed JSON and is_list indicates if it was a top-level list."""
    try:
        data = r.json()
    except Exception:
        return None, False
    return data, isinstance(data, list)


def show_parties_tab(base_url: str):
    st.header("Parties")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("List parties")
        r = api_get(base_url, "/api/parties/")
        if r is not None and r.ok:
            data, is_list = _normalize_response_json(r)
            if data is None:
                st.error("Unable to parse JSON response")
                return
            if is_list:
                rows = data
                count = len(rows)
            else:
                # allow either {'value': [...], 'Count': n} or {'items': [...]} or other shapes
                rows = data.get("value") or data.get("items") or []
                if rows is None:
                    rows = []
                count = data.get("Count", len(rows))
            st.write(f"Total: {count}")
            st.dataframe(rows)
        elif r is not None:
            st.error(f"Error listing parties: {r.status_code} {r.text}")

    with col2:
        st.subheader("Create party")
        with st.form("create_party"):
            name = st.text_input("Name")
            party_type = st.selectbox("Party type", ["supplier", "manufacturer", "distributor", "retailer", "customer"])
            tax_id = st.text_input("Tax ID")
            kyc = st.number_input("KYC verified (0-100)", min_value=0, max_value=100, value=0)
            submitted = st.form_submit_button("Create")
            if submitted:
                payload = {
                    "name": name,
                    "party_type": party_type,
                    "tax_id": tax_id or None,
                    "kyc_verified": kyc,
                }
                r = api_post(base_url, "/api/parties/", payload)
                if r is not None and r.status_code == 201:
                    st.success("Party created")
                    try:
                        st.json(r.json())
                    except Exception:
                        st.write(r.text)
                elif r is not None:
                    st.error(f"Create failed: {r.status_code} {r.text}")

    st.markdown("---")

    st.subheader("Update / Delete party")
    with st.form("modify_party"):
        pid = st.number_input("Party ID", min_value=1, value=1)
        new_name = st.text_input("New name (leave empty to keep)")
        new_kyc = st.number_input("New KYC (leave 0 to keep)", min_value=0, max_value=100, value=0)
        do_update = st.form_submit_button("Update")
        do_delete = st.form_submit_button("Delete")
        if do_update:
            updates = {}
            if new_name:
                updates["name"] = new_name
            if new_kyc:
                updates["kyc_verified"] = new_kyc
            if updates:
                r = api_put(base_url, f"/api/parties/{pid}", updates)
                if r is not None and r.ok:
                    st.success("Updated")
                    try:
                        st.json(r.json())
                    except Exception:
                        st.write(r.text)
                elif r is not None:
                    st.error(f"Update failed: {r.status_code} {r.text}")
            else:
                st.info("No updates provided")
        if do_delete:
            r = api_delete(base_url, f"/api/parties/{pid}")
            if r is not None and r.status_code in (200, 204):
                st.success("Deleted")
            elif r is not None:
                st.error(f"Delete failed: {r.status_code} {r.text}")


def show_relationships_tab(base_url: str):
    st.header("Relationships")

    st.subheader("List relationships")
    r = api_get(base_url, "/api/relationships/")
    if r is not None and r.ok:
        data, is_list = _normalize_response_json(r)
        if data is None:
            st.error("Unable to parse JSON response")
            return
        if is_list:
            st.dataframe(data)
        else:
            rows = data.get("value") or data.get("items") or []
            st.dataframe(rows)
    elif r is not None:
        st.error(f"Error listing relationships: {r.status_code} {r.text}")

    st.subheader("Create relationship")
    with st.form("create_rel"):
        from_id = st.number_input("From party ID", min_value=1, value=1)
        to_id = st.number_input("To party ID", min_value=1, value=1)
        rel_type = st.selectbox("Relationship type", ["supplies_to", "manufactures_for", "distributes_for", "sells_to"])
        submitted = st.form_submit_button("Create")
        if submitted:
            payload = {"from_party_id": from_id, "to_party_id": to_id, "relationship_type": rel_type}
            r = api_post(base_url, "/api/relationships/", payload)
            if r is not None and r.status_code == 201:
                st.success("Relationship created")
                try:
                    st.json(r.json())
                except Exception:
                    st.write(r.text)
            elif r is not None:
                st.error(f"Create failed: {r.status_code} {r.text}")

    st.subheader("Delete relationship")
    with st.form("delete_rel"):
        rid = st.number_input("Relationship ID", min_value=1, value=1)
        do_delete = st.form_submit_button("Delete")
        if do_delete:
            r = api_delete(base_url, f"/api/relationships/{rid}")
            if r is not None and r.status_code in (200, 204):
                st.success("Deleted")
            elif r is not None:
                st.error(f"Delete failed: {r.status_code} {r.text}")


def show_network_tab(base_url: str):
    st.header("Network / Counterparties")
    sid = st.number_input("Party ID", min_value=1, value=1)
    direction = st.selectbox("Direction", ["downstream", "upstream"])
    depth = st.slider("Depth", 1, 50, 10)
    if st.button("Get network"):
        r = api_get(base_url, f"/api/parties/{sid}/network", params={"direction": direction, "depth": depth})
        if r is not None and r.ok:
            data, is_list = _normalize_response_json(r)
            if data is None or is_list:
                st.error("Unexpected network response format")
                return
            st.subheader("Root Party")
            st.json(data.get("root_party"))
            st.subheader("Nodes")
            st.dataframe(data.get("nodes", []))
            st.subheader("Edges")
            st.dataframe(data.get("edges", []))
        elif r is not None:
            st.error(f"Network failed: {r.status_code} {r.text}")

    if st.button("Get counterparties"):
        r = api_get(base_url, f"/api/parties/{sid}/counterparties")
        if r is not None and r.ok:
            data, is_list = _normalize_response_json(r)
            if data is None:
                st.error("Unable to parse counterparties response")
                return
            if is_list:
                st.dataframe(data)
            else:
                rows = data.get("value") or data.get("items") or []
                st.dataframe(rows)
        elif r is not None:
            st.error(f"Counterparties failed: {r.status_code} {r.text}")


def show_stats_tab(base_url: str):
    st.header("Stats")
    r = api_get(base_url, "/api/stats")
    if r is not None and r.ok:
        try:
            st.json(r.json())
        except Exception:
            st.write(r.text)
    elif r is not None:
        st.error(f"Stats failed: {r.status_code} {r.text}")


def show_health_tab(base_url: str):
    st.header("Health")
    r = api_get(base_url, "/health")
    if r is not None and r.ok:
        try:
            st.json(r.json())
        except Exception:
            st.write(r.text)
    elif r is not None:
        st.error(f"Health failed: {r.status_code} {r.text}")


def main():
    st.title("KYCC - Lightweight Frontend")
    st.sidebar.title("Configuration")
    base_url = st.sidebar.text_input("API base URL", value="http://127.0.0.1:8000")

    tabs = st.tabs(["Parties", "Relationships", "Network", "Stats", "Health"])
    with tabs[0]:
        show_parties_tab(base_url)
    with tabs[1]:
        show_relationships_tab(base_url)
    with tabs[2]:
        show_network_tab(base_url)
    with tabs[3]:
        show_stats_tab(base_url)
    with tabs[4]:
        show_health_tab(base_url)


if __name__ == "__main__":
    main()
