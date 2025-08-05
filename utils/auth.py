import bcrypt
from supabase import create_client, Client
import streamlit as st
import os

# Supabase config
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    from dotenv import load_dotenv
    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def cadastrar_usuario(nome, username, senha, cargo):
    try:
        senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode('utf-8')

        data = {
            "nome": nome,
            "username": username,
            "senha_hash": senha_hash,
            "cargo": cargo,
            "aprovado": False  # precisa ser aprovado manualmente
        }

        resposta = supabase.table("usuarios").insert(data).execute()
        return {"success": True, "data": resposta.data}

    except Exception as e:
        return {"success": False, "error": str(e)}

def login_usuario(username, senha_input):
    try:
        resposta = supabase.table("usuarios").select("*").eq("username", username).execute()

        if not resposta.data:
            return {"success": False, "error": "Usuário não encontrado"}

        user = resposta.data[0]

        if not user.get("aprovado", False):
            return {"success": False, "error": "Usuário ainda não aprovado"}

        if bcrypt.checkpw(senha_input.encode(), user["senha_hash"].encode()):
            return {"success": True, "user": user}
        else:
            return {"success": False, "error": "Senha incorreta"}

    except Exception as e:
        return {"success": False, "error": str(e)}
    
def verificar_autenticacao(roles_permitidos=None):
    usuario = st.session_state.get("usuario")

    if not usuario:
        st.warning("Você precisa estar logado para acessar esta página.")
        st.stop()

    if not usuario.get("aprovado", False):
        st.error("⏳ Seu cadastro ainda não foi aprovado por um administrador.")
        st.stop()

    if roles_permitidos and usuario.get("cargo") not in roles_permitidos:
        st.error("🚫 Você não tem permissão para acessar esta página.")
        st.stop()

def logout():
    st.session_state.usuario_autenticado = False
    st.session_state.usuario = None
    st.success("Usuário desconectado com sucesso.")
    st.rerun()  # recarrega a app, forçando voltar para tela inicial (login)