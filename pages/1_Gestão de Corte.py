import streamlit as st
import pandas as pd
from streamlit_sortables import sort_items

from utils.auth import verificar_autenticacao, logout
verificar_autenticacao()

from utils.supabase import supabase, excluir_imagem_supabase
from utils.db import adicionar_na_fila, excluir_trabalhos_grupo
from utils.auxiliares import exibir_maquina

from streamlit_autorefresh import st_autorefresh
from collections import defaultdict

usuario = st.session_state.get("usuario", {}).get("nome", "desconhecido")
cargo_usuario = st.session_state.get("usuario", {}).get("cargo", "")


cargo_programador = cargo_usuario in ["Programador", "Gerente"]
cargo_pcp = cargo_usuario in ["PCP", "Gerente"]
cargo_operador = cargo_usuario in ["Operador", "PCP", "Gerente"]
cargo_empilhadeira = cargo_usuario in ["Empilhadeira", "Gerente"]


MAQUINAS = ["LASER 1", "LASER 2", "LASER 3", "LASER 4", "LASER 5", "LASER 6"]

st.set_page_config(page_title="Gestão de Corte", layout="wide")
st.title("🛠️ Gestão de Produção")

count = st_autorefresh(interval = 300000, key="autorefresh")

@st.dialog("Enviar CNC para Máquina")
def modal_enviar_cnc(item):
        st.markdown(f"### Enviar CNC `{item['cnc']}` para máquina")
        maquina_escolhida = st.selectbox("Selecione a máquina", MAQUINAS, key=f"modal_sel_maquina_{item['id']}")
        if st.button("🚀 Confirmar envio", key=f"confirmar_envio_{item['id']}"):
            adicionar_na_fila(maquina_escolhida, {
                "proposta": item["proposta"],
                "cnc": item["cnc"],
                "material": item["material"],
                "espessura": item["espessura"],
                "qtd_chapas": int(item["qtd_chapas"]),
                "tempo_total": item["tempo_total"],
                "caminho": item["caminho"],
                "programador": item.get("programador", "DESCONHECIDO"),
                "processos": item.get("processos", []),
                "gas": item.get("gas", None),
                "data_prevista": item["data_prevista"]
            },usuario)

            # Remove apenas o CNC individual das pendências
            supabase.table("trabalhos_pendentes") \
                .delete() \
                .eq("id", item["id"]) \
                .execute()

            st.success(f"CNC {item['cnc']} enviado para {maquina_escolhida}")
            st.rerun()

if st.session_state.get("usuario_autenticado"):
    if st.sidebar.button("🔒 Logout"):
        logout()
    st.sidebar.divider()

# =====================
# Sidebar - Trabalhos Pendentes
# =====================
st.sidebar.title("📋 Trabalhos Pendentes")
trabalhos_raw = (
    supabase.table("trabalhos_pendentes")
    .select("*")
    .eq("autorizado", True)
    .execute()
    .data or []
)

grupos = defaultdict(list)
for t in trabalhos_raw:
    grupos[t["grupo"]].append(t)

for grupo, itens in grupos.items():
    if st.session_state.get("status_envio_grupo") == grupo:
        st.success(f"Grupo {grupo} enviado com sucesso!")
        st.session_state["status_envio_grupo"] = None
        continue  # pula renderizar este grupo pois ele já foi processado
    trabalho = itens[0]
    # Primeira linha do título
    titulo_linha1 = (
        f"🔹 {trabalho.get('proposta', 'N/D')} | {trabalho.get('espessura', 'N/D')} mm | "
        f"{trabalho.get('material', 'N/D')} | x{len(itens)} CNCs | ⏱ {trabalho.get('tempo_total', 'N/D')}"
    )

    # Segunda linha do título
    data_fmt = "/".join(reversed(trabalho["data_prevista"].split("-")))
    if trabalho.get("gas"):
        gas_fmt = (f"💨 {trabalho.get('gas')}")
    else :
        gas_fmt = ""

    titulo_linha2 = (f"📅 {data_fmt} | ⚙️ {trabalho.get('processos')} | {gas_fmt}")        

    titulo = f"{titulo_linha1}\n\n{titulo_linha2}"

    with st.sidebar.expander(titulo, expanded=False):
        if cargo_pcp or cargo_operador:
            maquina_escolhida = st.selectbox("Enviar todos para:", MAQUINAS, key=f"sel_maquina_{grupo}")
            col_add, col_del = st.columns(2)
            with col_add:
                if st.button("➕ Enviar todos para a máquina", key=f"btn_add_todos_{grupo}"):
                    ids_para_deletar = []
                    for item in itens:
                        adicionar_na_fila(maquina_escolhida, {
                            "proposta": item["proposta"],
                            "cnc": item["cnc"],
                            "material": item["material"],
                            "espessura": item["espessura"],
                            "qtd_chapas": int(item["qtd_chapas"]),
                            "tempo_total": item["tempo_total"],
                            "caminho": item["caminho"],
                            "programador": item.get("programador", "DESCONHECIDO"),
                            "processos": item.get("processos", []),
                            "gas": item.get("gas", None),
                            "data_prevista": item["data_prevista"]
                        }, usuario)
                        ids_para_deletar.append(item["id"])

                    supabase.table("trabalhos_pendentes").delete().in_("id", ids_para_deletar).execute()
                    st.session_state["status_envio_grupo"] = grupo  # Marca que esse grupo foi enviado
            with col_del:
                if st.button("🖑 Excluir Trabalho", key=f"del_{grupo}"):
                    # 1. Obter todos os trabalhos do grupo
                    trabalhos_do_grupo = itens  # ← aqui está a correção

                    # 2. Excluir imagens (se houver)
                    for trabalho in trabalhos_do_grupo:
                        caminho = trabalho.get("caminho")
                        if caminho:
                            excluir_imagem_supabase(caminho)

                    # 3. Excluir os dados do grupo
                    excluir_trabalhos_grupo(grupo)

                    # 4. Feedback ao usuário
                    st.success("Trabalho excluído.")
                    st.rerun()


        for item in itens:
            with st.container(border=True):
                col1, col2 = st.columns([2, 2])
                with col1:
                    st.markdown(f"**Programador:** {item['programador']}")
                    st.markdown(f"**CNC:** {item['cnc']}")
                    st.markdown(f"**Qtd Chapas:** {item['qtd_chapas']}")
                    st.markdown(f"**Tempo Total:** {item['tempo_total']}")

                    if cargo_pcp or cargo_operador:
                        if st.button("📄 Enviar CNC para Máquina", key=f"btn_enviar_cnc_{item['id']}"):
                            modal_enviar_cnc(item)

                with col2:
                    if item["caminho"].startswith("http"):
                        st.image(item["caminho"], caption=f"CNC {item['cnc']}", use_container_width=True)
                    else:
                        st.warning("Imagem não encontrada.")
# =====================
# Painel Principal - Máquinas
# =====================
from utils.db import obter_todos_cortes_atuais, obter_todas_filas, obter_corte_atual, obter_fila

abas = ["🧩 Geral"] + [f"🔧 {m}" for m in MAQUINAS]
abas_componentes = st.tabs(abas)

for idx, aba in enumerate(abas):
    with abas_componentes[idx]:
        if idx == 0:
            # Aba Geral – carrega tudo de uma vez
            todos_cortes = obter_todos_cortes_atuais()
            todas_filas = obter_todas_filas()

            for maquina in MAQUINAS:
                exibir_maquina(maquina, modo="geral",
                               dados_corte=todos_cortes.get(maquina),
                               fila_maquina=todas_filas.get(maquina, []))
        else:
            # Apenas essa máquina individual
            maquina = MAQUINAS[idx - 1]  # porque "Geral" está na posição 0
            corte = obter_corte_atual(maquina)
            fila = obter_fila(maquina)
            exibir_maquina(maquina, modo="individual",
                           dados_corte=corte, fila_maquina=fila)