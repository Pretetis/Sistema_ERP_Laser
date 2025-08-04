import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit import session_state as ss
from utils.auth import verificar_autenticacao, logout
verificar_autenticacao()

from utils.auxiliares import renderizar_trabalhos_pendentes, renderizar_corte_atual, renderizar_maquina_fragment

usuario = st.session_state.get("usuario", {}).get("nome", "desconhecido")
cargo_usuario = st.session_state.get("usuario", {}).get("cargo", "")
MAQUINAS = ["LASER 1", "LASER 2", "LASER 3", "LASER 4", "LASER 5", "LASER 6"]

cargo_programador = cargo_usuario in ["Programador", "Gerente"]
cargo_pcp = cargo_usuario in ["PCP", "Gerente"]
cargo_operador = cargo_usuario in ["Operador", "PCP", "Gerente"]
cargo_empilhadeira = cargo_usuario in ["Empilhadeira", "Gerente"]

#logo_img = "images\logo-microns.png"
#st.logo(logo_img, size="large")

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
        container_corte = st.empty()
        container_fila = st.empty()

        def atualizar_maquina(m=maquina):
            with container_corte:
                renderizar_corte_atual(m, gatilho=ss.get(f"gatilho_corte_{m}", 0))
            with container_fila:
                renderizar_maquina_fragment(m, modo="fila_apenas", gatilho=ss.get(f"gatilho_fila_{m}", 0))

        st.session_state[f"atualizar_maquina_fn_{maquina}"] = atualizar_maquina
        atualizar_maquina()
