import streamlit as st

def barra_navegacao():
    st.markdown(
        """
        <style>
        .nav-container {
            background-color: #f0f2f6;
            padding: 10px 0;
            border-bottom: 1px solid #ddd;
            margin-bottom: 25px;
        }
        .nav-button {
            display: inline-block;
            margin: 0 15px;
            font-size: 16px;
            font-weight: 600;
            color: #0366d6;
            text-decoration: none;
        }
        .nav-button:hover {
            text-decoration: underline;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        st.page_link("app.py", label="🏭 Gestão de Produção", icon="📋")
    with col2:
        st.page_link("pages/1_Gestão de corte.py", label="📤 Enviar Programas CNC", icon="📤")