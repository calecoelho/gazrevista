"""
Gazeta do Povo Revista - app interno (Streamlit).

Este arquivo só cuida de duas coisas: pedir a senha e montar o menu lateral.
O conteúdo de cada página está na pasta paginas/.

Para abrir no seu computador:   streamlit run app.py
"""
import streamlit as st

import comum

st.set_page_config(page_title="Gazeta Revista", page_icon="📰", layout="centered")

comum.preparar()
comum.pedir_senha()  # nada abaixo roda sem a senha certa

menu = st.navigation(
    [
        st.Page("paginas/revista.py", title="Montar a revista", icon="📰", url_path="revista", default=True),
        st.Page("paginas/roteiro.py", title="Roteiro para redes", icon="🎬", url_path="roteiro"),
        st.Page("paginas/tutorial.py", title="Tutorial", icon="📖", url_path="tutorial"),
    ]
)

with st.sidebar:
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()

menu.run()
