import streamlit as st
from supabase import create_client, Client

# Initialize Supabase Connection
# This uses the secrets from .streamlit/secrets.toml
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Failed to connect to Supabase: {e}")
    st.stop()