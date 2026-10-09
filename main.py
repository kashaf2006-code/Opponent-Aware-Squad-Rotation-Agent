import streamlit as st
st.set_page_config(page_title="My Streamlit App", page_icon=":smiley:", layout="wide")

st.title("Welcome to My Streamlit App")

st.title("🏏 OACSRA")
st.subheader("Opponent-Aware Cricket Squad Rotation Agent")

st.write(
    "Decision-support system for cricket squad selection "
    "and rotation based on workload, performance, fixture priority, "
    "and opponent difficulty."
)

st.success("OACSRA environment is working successfully!")