"""
Coisas que todas as páginas usam: segredos (senha e chave da OpenAI) e a tela de senha.
"""
import hmac
import os
import time

import streamlit as st

import gerar_texto_publicacao as gtp


def segredo(nome):
    """Procura primeiro nos 'Secrets' do Streamlit e depois nas variáveis de ambiente (.env)."""
    try:
        valor = st.secrets.get(nome)
    except Exception:  # noqa: BLE001  (sem arquivo de secrets: tudo bem)
        valor = None
    return str(valor) if valor else os.environ.get(nome)


def preparar():
    """Lê o .env (quando roda no seu computador) e deixa a chave da OpenAI onde os scripts procuram."""
    gtp.carregar_env()
    chave = segredo("OPENAI_API_KEY")
    if chave:
        os.environ["OPENAI_API_KEY"] = chave


def pedir_senha():
    """Só deixa passar quem digitou a senha certa. Se não houver senha configurada, bloqueia."""
    esperada = segredo("APP_PASSWORD")
    if not esperada:
        st.error(
            "Este app ainda não tem senha configurada. Defina `APP_PASSWORD` nos Secrets "
            "(ou no arquivo .env, se estiver rodando no seu computador)."
        )
        st.stop()
    if st.session_state.get("entrou"):
        return
    st.title("📰 Gazeta Revista")
    with st.form("entrada"):
        digitada = st.text_input("Senha", type="password")
        enviar = st.form_submit_button("Entrar")
    if enviar:
        if hmac.compare_digest(digitada.encode("utf-8"), esperada.encode("utf-8")):
            st.session_state["entrou"] = True
            st.rerun()
        time.sleep(1.5)  # atrapalha quem fica tentando senhas
        st.error("Senha incorreta.")
    st.stop()
