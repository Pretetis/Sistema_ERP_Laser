import streamlit as st
from pathlib import Path
import pandas as pd
from utils.Junta_Trabalhos import carregar_trabalhos
from utils.db import (
    criar_banco, adicionar_na_fila, obter_fila,
    obter_corte_atual, iniciar_corte, finalizar_corte
)
from utils.visualizacao import gerar_preview_pdf


MAQUINAS = ["LASER 1", "LASER 2", "LASER 3", "LASER 4", "LASER 5", "LASER 6"]

from streamlit_autorefresh import st_autorefresh

# Atualiza automaticamente a cada 7 segundos
st_autorefresh(interval=7000, key="data_refresh")

from utils.navegacao import barra_navegacao

st.set_page_config(page_title="Minha Página", layout="wide")

barra_navegacao()  # Exibe a barra no topo


criar_banco()
st.set_page_config(page_title="Gestão de Corte", layout="wide")
st.title("🛠️ Gestão de Produção")

# =====================
# Sidebar - Trabalhos Agrupados
# =====================
st.sidebar.title("📋 Trabalhos Pendentes")
trabalhos = carregar_trabalhos(pasta="autorizados")

if not trabalhos:
    st.sidebar.info("Nenhum trabalho pendente no momento.")
    
for trabalho in trabalhos:
    with st.sidebar.expander(
        f"🔹 {trabalho['Proposta']} | {trabalho['Espessura']} mm | {trabalho['Material']} | x {trabalho['Qtd Total']} | ⏱ {trabalho['Tempo Total']}"
    ):

        for item in trabalho["Detalhes"]:
            with st.container(border=True):
                col1, col2 = st.columns([2, 2])

                with col1:
                    st.markdown(f"**Programador:** {item['Programador']}")
                    st.markdown(f"**CNC:** {item['CNC']}")
                    st.markdown(f"**Qtd Chapas:** {item['Qtd Chapas']}")
                    st.markdown(f"**Tempo Total:** {item['Tempo Total']}")

                with col2:
                    caminho_pdf = item.get("Caminho PDF") or item.get("Caminho")
                    if caminho_pdf and Path(caminho_pdf).exists():
                        preview_path = gerar_preview_pdf(caminho_pdf)
                        if preview_path:
                            st.image(preview_path, caption=f"CNC {item['CNC']}", use_container_width="auto")
                        else:
                            st.warning("Erro ao gerar preview.")
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
                    "Tempo Total": item["Tempo Total"]
                })

            # 🔴 Remove o arquivo do grupo após o envio
            from pathlib import Path
            caminho_txt = Path("autorizados") / f"{trabalho['Grupo']}.txt"
            if caminho_txt.exists():
                caminho_txt.unlink()

            st.success(f"Trabalho enviado para {maquina_escolhida}")
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
            if st.button("✅ Finalizar Corte Atual", key=f"fim_{maquina}"):
                finalizar_corte(maquina)
                st.success("Corte finalizado")
                st.rerun()
        else:
            st.markdown("_Nenhum corte em andamento_")

        if fila:
            st.markdown("### 📋 Fila de Espera")
            df = pd.DataFrame(fila, columns=["ID", "Máquina", "Proposta", "CNC", "Material", "Espessura", "Quantidade", "Tempo Total"])
            st.dataframe(df.drop(columns=["Máquina"]), use_container_width=True, hide_index=True)

            opcoes = {f"{row[2]} | CNC {row[3]}": row[0] for row in fila}
            escolha = st.selectbox("Escolha próximo CNC:", list(opcoes.keys()), key=f"escolha_{maquina}")
            if st.button("▶️ Iniciar Corte", key=f"iniciar_{maquina}"):
                iniciar_corte(maquina, opcoes[escolha])
                st.success("Corte iniciado")
                st.rerun()
        else:
            st.markdown("_Fila vazia_")