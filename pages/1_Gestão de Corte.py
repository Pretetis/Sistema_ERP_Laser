import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit import session_state as ss
from utils.auth import verificar_autenticacao, logout
from utils.storage import supabase
verificar_autenticacao()

from utils.auxiliares import renderizar_maquina_fragment, renderizar_trabalhos_pendentes

usuario = st.session_state.get("usuario", {}).get("nome", "desconhecido")
cargo_usuario = st.session_state.get("usuario", {}).get("cargo", "")
MAQUINAS = ["LASER 1", "LASER 2", "LASER 3", "LASER 4", "LASER 5", "LASER 6"]

cargo_programador = cargo_usuario in ["Programador", "Gerente"]
cargo_pcp = cargo_usuario in ["PCP", "Gerente"]
cargo_operador = cargo_usuario in ["Operador", "PCP", "Gerente"]
cargo_empilhadeira = cargo_usuario in ["Empilhadeira", "Gerente"]

st.set_page_config(page_title="Gestão de Corte", layout="wide")
#st.title("🛠️ Gestão de Produção")

count = st_autorefresh(interval = 300000, key="autorefresh")

if st.session_state.get("usuario_autenticado"):
    col_logout, col_usuario, col_cargo = st.sidebar.columns([1, 2, 2])

    with col_logout:
        if st.button(":material/Key_Off: Logout", use_container_width=True):
            logout()

    with col_usuario:
        with st.container(border=True):
            st.markdown(":material/Id_Card: **Usuário:** " + usuario)

    with col_cargo:
        with st.container(border=True):
            st.markdown("**Cargo:** " + cargo_usuario)

    st.sidebar.divider()

import time

start = time.time()
corte = supabase.table("corte_atual").select("*").eq("maquina", MAQUINAS[0]).execute().data
st.write(f"obter_corte_atual levou {time.time() - start:.2f}s")

start = time.time()
fila = supabase.table("fila_maquinas").select("*").eq("maquina", MAQUINAS[0]).execute().data
st.write(f"obter_fila_corte levou {time.time() - start:.2f}s")


# =====================
# Sidebar - Trabalhos Pendentes
# =====================
with st.sidebar:
    st.title(":material/Format_List_Bulleted: Trabalhos Pendentes")
    container_pendentes = st.empty()

    def atualizar_trabalhos_pendentes():
        with container_pendentes:
            renderizar_trabalhos_pendentes(gatilho=ss.get("atualizar_trabalhos_pendentes", 0))
    
    st.session_state["atualizar_trabalhos_pendentes_fn"] = atualizar_trabalhos_pendentes
    atualizar_trabalhos_pendentes()

# =====================
# Painel Principal - Máquinas
# =====================
abas_componentes = st.tabs([f"🔧 {m}" for m in MAQUINAS])

containers_maquinas = {}

for idx, maquina in enumerate(MAQUINAS):
    with abas_componentes[idx]:
        container = st.empty()
        containers_maquinas[maquina] = container

        def atualizar_maquina(m=maquina):  # 👈 importante para capturar corretamente
            with containers_maquinas[m]:
                renderizar_maquina_fragment(m, modo="individual", gatilho=0)

        st.session_state[f"atualizar_maquina_fn_{maquina}"] = atualizar_maquina
        atualizar_maquina()
