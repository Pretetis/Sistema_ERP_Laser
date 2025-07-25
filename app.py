import streamlit as st
from utils.auth import login_usuario, cadastrar_usuario

st.set_page_config(page_title="Sistema Login", layout="centered", initial_sidebar_state="collapsed")

# Inicializar sessão
if "usuario_autenticado" not in st.session_state:
    st.session_state.usuario_autenticado = False
if "usuario" not in st.session_state:
    st.session_state.usuario = None

# Página principal com Login ou Cadastro
aba_login, aba_cadastro = st.tabs(["Login", "Cadastro"])

with aba_login:
    st.title("Login")
    username = st.text_input("Username", key="login_username")
    senha = st.text_input("Senha", type="password", key="login_senha")

    if st.button("Entrar"):
        resultado = login_usuario(username, senha)
        if resultado["success"]:
            st.session_state.usuario_autenticado = True
            st.session_state.usuario = resultado["user"]
            st.success("Login realizado com sucesso!")
            st.switch_page("pages/1_Gestão de Corte.py")
        else:
            st.error(resultado["error"])

with aba_cadastro:
    st.title("Cadastro de Novo Usuário")

    nome = st.text_input("Nome completo", key="cadastro_nome")
    novo_username = st.text_input("Nome de usuário", key="cadastro_username")
    email = st.text_input("Email", key="cadastro_email")
    nova_senha = st.text_input("Senha", type="password", key="cadastro_senha")
    confirmar_senha = st.text_input("Confirmar Senha", type="password", key="confirmar_senha")
    cargo = st.selectbox("Cargo", ["Programador", "PCP", "Operador", "Gerente"], key="cadastro_cargo")

    if st.button("Cadastrar"):
        if not nome or not novo_username or not email or not nova_senha or not confirmar_senha:
            st.warning("Preencha todos os campos.")
        elif nova_senha != confirmar_senha:
            st.error("As senhas não coincidem. Tente novamente.")
        else:
            resultado = cadastrar_usuario(nome, novo_username, email, nova_senha, cargo)
            if resultado["success"]:
                st.success("Cadastro realizado! Aguarde aprovação do administrador.")
            else:
                st.error(f"Erro ao cadastrar: {resultado['error']}")
