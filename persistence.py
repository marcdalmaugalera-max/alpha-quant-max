import json
import streamlit as st


def _key(name):
    return f"_session_{name}"


def get(name, default=None):
    default = default or {}
    if _key(name) not in st.session_state:
        st.session_state[_key(name)] = dict(default)
    return st.session_state[_key(name)]


def set(name, data):
    st.session_state[_key(name)] = data


def delete(name):
    if _key(name) in st.session_state:
        del st.session_state[_key(name)]


def export_portfolio(portfolio):
    return json.dumps(portfolio, indent=2, ensure_ascii=False)


def export_watchlist(watchlist):
    return json.dumps(watchlist, indent=2, ensure_ascii=False)