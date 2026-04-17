import os


def get_secret(key: str, default: str = "") -> str:
    """Read from st.secrets (Streamlit Cloud) with fallback to os.environ (local .env)."""
    try:
        import streamlit as st
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)
