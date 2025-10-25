import os
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Case Study Console", layout="wide")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Settings")
    api_base = st.text_input("API Base", API_BASE)
    api_key = st.text_input("API Key (required for writes)", value=os.getenv("API_KEY_UI", "letmein123"))
    use_llm = st.checkbox("Use local LLM (Ollama)", value=True)
    model_name = st.text_input("Ollama Model", os.getenv("OLLAMA_MODEL", "llama3.2:3b"))

    st.caption("Health:")
    try:
        h = requests.get(f"{api_base}/health", timeout=5).json()
        st.success(h)
    except Exception as e:
        st.error(f"API unreachable: {e}")

st.title("🧮 Application Decision Console")

# ---------------- Tabs ----------------
tab_create, tab_upload, tab_run, tab_chat = st.tabs(["1) Create", "2) Upload", "3) Run", "4) Chat"])

# 1) Create
with tab_create:
    st.subheader("Create Application")
    app_id = st.text_input("Application ID", "APP-DEMO-1")
    full_name = st.text_input("Full Name", "Demo User")
    age = st.number_input("Age", min_value=0, max_value=120, value=30)
    address = st.text_input("Address", "DXB")
    employment_status = st.selectbox("Employment Status", ["employed", "self_employed", "student", "unemployed", "retired"])
    income = st.number_input("Net Monthly Income", min_value=0, value=5000)
    go = st.button("Create")
    if go:
        payload = {
            "application_id": app_id,
            "full_name": full_name,
            "age": int(age),
            "address": address,
            "employment_status": employment_status,
            "net_monthly_income": float(income)
        }
        try:
            r = requests.post(f"{api_base}/applications", json=payload, headers={"X-API-Key": api_key}, timeout=10)
            st.write(r.status_code, r.text)
        except Exception as e:
            st.error(e)

# 2) Upload
with tab_upload:
    st.subheader("Upload Document(s)")
    app_id_u = st.text_input("Application ID", "APP-DEMO-1", key="upload_id")
    files = st.file_uploader("Select files", accept_multiple_files=True, type=None)
    if st.button("Upload"):
        if not files:
            st.warning("Choose at least one file.")
        else:
            mfiles = []
            for f in files:
                ctype = getattr(f, "type", None) or "application/octet-stream"
                mfiles.append(("files", (f.name, f.getvalue(), ctype)))
            try:
                r = requests.post(
                    f"{api_base}/applications/{app_id_u}/upload",
                    files=mfiles,
                    headers={"X-API-Key": api_key},
                    timeout=60
                )
                st.write(r.status_code, r.text)
            except Exception as e:
                st.error(e)

# 3) Run
with tab_run:
    st.subheader("Run Decision")
    app_id_r = st.text_input("Application ID", "APP-DEMO-1", key="run_id")
    if st.button("Run"):
        try:
            r = requests.post(
                f"{api_base}/applications/{app_id_r}/run",
                headers={"X-API-Key": api_key},
                timeout=60
            )
            if r.ok:
                data = r.json()
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Status", data.get("status"))
                    st.json(data.get("eligibility", {}))
                with c2:
                    st.markdown("**Validation**")
                    st.code("\n".join(["✅ " + x for x in data["validation"]["pass_checks"]]))
                    if data["validation"]["warn_checks"]:
                        st.code("\n".join(["⚠️ " + x for x in data["validation"]["warn_checks"]]))
                    if data["validation"]["fail_checks"]:
                        st.code("\n".join(["❌ " + x for x in data["validation"]["fail_checks"]]))
                st.markdown("**Recommendations**")
                for rec in data.get("recommendations", []):
                    st.write("•", rec)
                st.caption(data.get("rationale", ""))
            else:
                st.write(r.status_code, r.text)
        except Exception as e:
            st.error(e)

# 4) Chat (simple input + send)
with tab_chat:
    st.subheader("Chat with Underwriting Agent")
    app_id_c = st.text_input("Application ID", "APP-DEMO-1", key="chat_id")

    # simple session history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Show history
    for who, msg in st.session_state.chat_history:
        if who == "user":
            st.markdown(f"**You:** {msg}")
        else:
            st.markdown(f"**Agent:** {msg}")

    user_msg = st.text_input("Message", "summarize my documents and explain latest decision", key="chat_input")
    if st.button("Send"):
        if not app_id_c.strip():
            st.warning("Please enter an Application ID.")
        elif not user_msg.strip():
            st.warning("Please enter a message.")
        else:
            try:
                payload = {
                    "application_id": app_id_c.strip(),
                    "messages": [{"role": "user", "content": user_msg.strip()}],
                    "use_llm": bool(use_llm)
                }
                r = requests.post(
                    f"{api_base}/chat",
                    json=payload,
                    headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                    timeout=90
                )
                if r.ok:
                    data = r.json()
                    reply = data.get("reply", "")
                    st.session_state.chat_history.append(("user", user_msg))
                    st.session_state.chat_history.append(("agent", reply))
                    try:
                        # Streamlit >= 1.30
                        st.rerun()
                    except AttributeError:
                        # Fallback for older versions
                        import streamlit as _st
                        if hasattr(_st, "experimental_rerun"):
                            _st.experimental_rerun()
                        else:
                            # If neither exists, just clear the input to indicate progress
                            st.session_state["chat_input"] = ""
                else:
                    st.error(f"{r.status_code} {r.text}")
            except Exception as e:
                st.error(e)
