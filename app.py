import streamlit as st
from supabase import create_client
import pandas as pd
import time

# ── 0) Page title ─────────────────────────────────────────────────────────────
st.title("CRGE Historical Database Explorer")

# ── 1) Supabase connection info from Streamlit secrets ─────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# ── 2) Authentication flow using Supabase Auth ───────────────────────────────
if "access_token" not in st.session_state:
    st.subheader("🔐 Sign In")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Log in"):
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        try:
            auth_res = client.auth.sign_in_with_password({"email": email, "password": password})
            token = auth_res.session.access_token
            st.session_state["access_token"] = token
            # trigger a rerun by changing a query parameter
            st.query_params(_rerun=int(time.time()))
            st.stop()
        except Exception as e:
            st.error(f"Login failed: {e}")
    # halt script until successful login
    st.stop()

# ── 3) Create authenticated Supabase client ─────────────────────────────────
@st.cache_resource
def get_supabase(token: str):
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    sb.postgrest.auth(token)
    return sb

supabase = get_supabase(st.session_state["access_token"])

# ── 4) Data helpers ───────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_options(table: str, column: str):
    resp = supabase.table(table).select(column).execute()
    rows = resp.data or []
    values = sorted({row[column] for row in rows if column in row})
    return ["All"] + values

@st.cache_data(ttl=600)
def fetch_entries(table: str, country: str, period: str, section: str, search: str):
    q = (
        supabase
          .table(table)
          .select("*")
          .order("section_num")
          .order("entry_num")
    )
    if country != "All":
        q = q.eq("country", country)
    if period != "All":
        q = q.eq("period", period)
    if section != "All":
        q = q.eq("section", section)
    if search:
        q = q.ilike("entry", f"%{search}%")
    return q.execute().data or []

# ── 5) UI filters ─────────────────────────────────────────────────────────────
country = st.selectbox("Country", load_options("English", "country"))
period  = st.selectbox("Period",  load_options("English", "period"))
section = st.selectbox("Section", load_options("English", "section"))
search  = st.text_input("Search entries…")

# ── 6) Fetch and render data ─────────────────────────────────────────────────
eng_rows  = fetch_entries("English", country, period, section, search)
orig_rows = fetch_entries("OriginalLanguage", country, period, section, search)

def render(rows, label: str):
    st.header(label)
    if not rows:
        st.write("No entries found.")
        return
    df = pd.DataFrame(rows)
    for sec_val, grp in df.groupby("section", sort=False):
        st.subheader(f"Section: {sec_val}")
        for entry in grp.get("entry", []):
            st.write(entry)

render(eng_rows,  "English")
render(orig_rows, "Original Language")

# ── 7) Logout ────────────────────────────────────────────────────────────────
if st.button("🔒 Log out"):
    del st.session_state["access_token"]
    st.query_params(_rerun=int(time.time()))
    st.stop()