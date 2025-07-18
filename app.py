import streamlit as st
from pathlib import Path
import pandas as pd
from utils.Junta_Trabalhos import carregar_trabalhos
from utils.google_drive_utils import deletar_txt_drive 
from utils.db import (
    criar_banco, adicionar_na_fila, obter_fila,
    obter_corte_atual, iniciar_corte, finalizar_corte,
    excluir_da_fila, excluir_do_corte,
    excluir_pendente, retornar_para_pendentes,
    registrar_trabalho_enviado, retornar_item_da_fila_para_pendentes
)

MAQUINAS = ["LASER 1", "LASER 2", "LASER 3", "LASER 4", "LASER 5", "LASER 6"]

from streamlit_autorefresh import st_autorefresh

# Atualiza automaticamente a cada 7 segundos
st_autorefresh(interval=7000, key="data_refresh")

from utils.navegacao import barra_navegacao

st.set_page_config(page_title="Gestão de Corte", layout="wide")

barra_navegacao()  # Exibe a barra no topo

criar_banco()
st.set_page_config(page_title="Gestão de Corte", layout="wide")
st.title("🛠️ Gestão de Produção")

# =====================
# Sidebar - Trabalhos Agrupados
# =====================
st.sidebar.title("📋 Trabalhos Pendentes")
trabalhos = carregar_trabalhos()
trabalhos_pendentes = trabalhos["trabalhos_pendentes"]

for trabalho in trabalhos:
    titulo = (
        f"🔹 {trabalho['Proposta']} | {trabalho['Espessura']} mm | {trabalho['Material']} "
        f"| x {trabalho['Qtd Total']} | ⏱ {trabalho['Tempo Total']}"
    )

    if trabalho.get("Data Prevista"):
        try:
            data_fmt = "/".join(reversed(trabalho["Data Prevista"].split("-")))
            titulo += f" | 📅 {data_fmt}"
        except:
            pass

    if trabalho.get("Processos"):
        titulo += f" | ⚙️ {trabalho['Processos']}"

    with st.sidebar.expander(titulo):
        for item in trabalho["Detalhes"]:
            with st.container(border=True):
                col1, col2 = st.columns([2, 2])

                with col1:
                    st.markdown(f"**Programador:** {item['Programador']}")
                    st.markdown(f"**CNC:** {item['CNC']}")
                    st.markdown(f"**Qtd Chapas:** {item['Qtd Chapas']}")
                    st.markdown(f"**Tempo Total:** {item['Tempo Total']}")

                with col2:
                        caminho_pdf = item.get("Caminho")
                        if caminho_pdf:
                            st.image(caminho_pdf, caption=f"CNC {item['CNC']}", use_container_width="auto")
                        else:
                            st.warning("Arquivo PDF não encontrado.")

        maquina_escolhida = st.selectbox("Enviar para:", MAQUINAS, key=f"sel_maquina_{trabalho['Grupo']}")
        if st.button("➕ Adicionar à máquina", key=f"btn_{trabalho['Grupo']}"):
            for item in trabalho["Detalhes"]:
                adicionar_na_fila(maquina_escolhida, {
                    "Proposta": trabalho["Proposta"],
                    "CNC": item["CNC"],
                    "Material": trabalho["Material"],
                    "Espessura": trabalho["Espessura"],
                    "Quantidade": item["Qtd Chapas"],
                    "Tempo Total": item["Tempo Total"],
                    "Caminho": item.get("Caminho", "")
                })

                # NOVO: registra os dados completos para possível retorno
                registrar_trabalho_enviado(
                    grupo=trabalho["Grupo"],
                    proposta=trabalho["Proposta"],
                    cnc=item["CNC"],
                    material=trabalho["Material"],
                    espessura=trabalho["Espessura"],
                    quantidade=item["Qtd Chapas"],
                    tempo_total=item["Tempo Total"],
                    programador=item.get("Programador", "DESCONHECIDO"),
                    data_prevista=trabalho.get("Data Prevista"),
                    processos=trabalho.get("Processos"),
                )

            # Remove o arquivo após registrar
            caminho_txt = Path("autorizados") / f"{trabalho['Grupo']}.txt"
            if caminho_txt.exists():
                caminho_txt.unlink()
                deletar_txt_drive (caminho_txt.name)

            st.success(f"Trabalho enviado para {maquina_escolhida}")
            st.rerun()

        if st.button("🗑 Excluir Pendente", key=f"exc_pend_{trabalho['Grupo']}"):
            excluir_pendente(trabalho["Grupo"])
            deletar_txt_drive (f"{trabalho['Grupo']}.txt")
            st.success("Trabalho pendente excluído")
            st.rerun()

# =====================
# Painel Principal - Máquinas
# =====================
st.markdown("---")
cols = st.columns(1)

for i, maquina in enumerate(MAQUINAS):
    with cols[i % 1]:
        st.markdown(f"## 🔧 {maquina}")

        corte = obter_corte_atual(maquina)
        fila = obter_fila(maquina)

        if corte:
            st.markdown(
                f"**🔹 Corte Atual:** {corte[1]} | CNC {corte[2]} | {corte[3]} | {corte[4]} mm"
            )
            col_fim, col_ret, col_exc = st.columns(3)

            with col_fim:
                if st.button("✅ Finalizar Corte Atual", key=f"fim_{maquina}"):
                    finalizar_corte(maquina)
                    st.success("Corte finalizado")
                    st.rerun()

            with col_ret:
                if st.button("🔁 Retornar para Pendentes", key=f"ret_{maquina}"):
                    retornar_para_pendentes(maquina)
                    st.success("Trabalho retornado para pendentes")
                    st.rerun()

            with col_exc:
                if st.button("🖑 Excluir Corte Atual", key=f"exc_{maquina}"):
                    excluir_do_corte(maquina)
                    st.success("Corte excluído")
                    st.rerun()
        else:
            st.markdown("_Nenhum corte em andamento_")

        if fila:
            st.markdown("### 📋 Fila de Espera")

            dados_fila = []
            opcoes = {}

            for item in fila:
                item_dict = {
                    "ID": item[0],
                    "Máquina": item[1],
                    "Proposta": item[2],
                    "CNC": item[3],
                    "Material": item[4],
                    "Espessura": item[5],
                    "Quantidade": item[6],
                    "Tempo": item[7],
                    "Caminho": item[8] if len(item) > 8 else "",  # proteção caso banco antigo
                    "Local Separado": ""
                }

                dados_fila.append(item_dict)
                chave_opcao = f"{item_dict['Proposta']} | CNC {item_dict['CNC']}"
                opcoes[chave_opcao] = item_dict["ID"]

            df_visual = pd.DataFrame(dados_fila)

            # Mostrar o DataFrame com colunas desejadas 
            config = {
                "Caminho": st.column_config.ImageColumn(),
            }

            st.data_editor(
                df_visual[["Local Separado", "Proposta", "Material", "Espessura", "CNC", "Quantidade", "Tempo", "Caminho"]],
                column_config=config,
                hide_index=True,
                use_container_width=True
            )

            # Botões
            escolha = st.selectbox("Escolha próximo CNC:", list(opcoes.keys()), key=f"escolha_{maquina}")
            col_iniciar, col_ret, col_excluir_fila = st.columns(3)

            with col_iniciar:
                if st.button("▶️ Iniciar Corte", key=f"iniciar_{maquina}"):
                    iniciar_corte(maquina, opcoes[escolha])
                    st.success("Corte iniciado")
                    st.rerun()

            with col_ret:
                if st.button("🔁 Retornar CNC para Pendentes", key=f"ret_fila_{maquina}"):
                    retornar_item_da_fila_para_pendentes(opcoes[escolha])
                    st.success("Item da fila retornado para pendentes")
                    st.rerun()

            with col_excluir_fila:
                if st.button("🖑 Excluir da Fila", key=f"exc_fila_{maquina}"):
                    excluir_da_fila(maquina, opcoes[escolha])
                    st.success("Item excluído da fila")
                    st.rerun()
        else:
            st.markdown("_Fila vazia_")