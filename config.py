import os


def get_secret(key: str, default: str = "") -> str:
    """Read from st.secrets (Streamlit Cloud) with fallback to os.environ (local .env)."""
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val is not None:
            return str(val)
    except Exception:
        pass
    return os.environ.get(key, default)
