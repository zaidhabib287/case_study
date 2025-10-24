import os
import streamlit as st, requests, json

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Case Study Demo", layout="wide")
st.title("Application Portal")

with st.form("apply"):
    app_id = st.text_input("Application ID", "APP-001")
    full_name = st.text_input("Full Name")
    age = st.number_input("Age", 18, 100, 30)
    address = st.text_input("Address")
    household = st.text_area("Household JSON (optional)", "[]")
    if st.form_submit_button("Create Application"):
        payload = dict(
            application_id=app_id,
            full_name=full_name,
            age=age,
            address=address,
            household=json.loads(household),
        )
        try:
            r = requests.post(f"{API_BASE}/applications", json=payload, timeout=10)
            r.raise_for_status()
            st.success(r.json())
        except requests.exceptions.RequestException as e:
            st.error(f"API error: {e}")
            if r is not None:
                st.code(r.text)
        st.success(r.json())

st.subheader("Upload Documents")
app_for_upload = st.text_input("Application ID (for upload)", "APP-001")
files = st.file_uploader("Upload PDFs/Images/Excels", accept_multiple_files=True)
if st.button("Upload"):
    if files:
        up = [("files", (f.name, f.read())) for f in files]
        try:
            r = requests.post(f"{API_BASE}/applications", json=payload, timeout=10)
            r.raise_for_status()
            st.success(r.json())
        except requests.exceptions.RequestException as e:
            st.error(f"API error: {e}")
            if r is not None:
                st.code(r.text)
        st.success(r.json())

st.subheader("Run Decision")
app_for_run = st.text_input("Application ID (to run)", "APP-001")
if st.button("Run"):
    try:
        r = requests.post(f"{API_BASE}/applications", json=payload, timeout=10)
        r.raise_for_status()
        st.success(r.json())
    except requests.exceptions.RequestException as e:
        st.error(f"API error: {e}")
        if r is not None:
            st.code(r.text)
    st.json(r.json())
