import streamlit as st
import pandas as pd
from collections import defaultdict
from Junta_Trabalhos import carregar_trabalhos

# Define máquinas disponíveis
MAQUINAS = ["LASER 1", "LASER 2", "LASER 3", "LASER 4", "LASER 5", "LASER 6"]

# Inicialização do estado
if "fila_maquinas" not in st.session_state:
    st.session_state.fila_maquinas = defaultdict(list)
if "corte_atual" not in st.session_state:
    st.session_state.corte_atual = {}

st.set_page_config(page_title="Gestão de Corte", layout="wide")
st.title("🛠️ Gestão de Produção")

# =====================
# Sidebar - Trabalhos Agrupados
# =====================
st.sidebar.title("📋 Trabalhos Agrupados")
trabalhos = carregar_trabalhos()

for trabalho in trabalhos:
    with st.sidebar.expander(
        f"🔹 {trabalho['Proposta']} | {trabalho['Espessura']} mm | {trabalho['Material']} | x {trabalho['Qtd Total']} | ⏱ {trabalho['Tempo Total']}"
    ):
        st.dataframe(
            pd.DataFrame(trabalho["Detalhes"])[["Programador", "CNC", "Qtd Chapas", "Tempo Total", "Caminho PDF"]],
            use_container_width=True,
            hide_index=True,
        )
        maquina_escolhida = st.selectbox("Enviar para:", MAQUINAS, key=f"sel_maquina_{trabalho['Grupo']}")
        if st.button("➕ Adicionar à máquina", key=f"btn_{trabalho['Grupo']}"):
            for item in trabalho["Detalhes"]:
                st.session_state.fila_maquinas[maquina_escolhida].append({
                    "Proposta": trabalho["Proposta"],
                    "CNC": item["CNC"],
                    "Material": trabalho["Material"],
                    "Espessura": trabalho["Espessura"],
                    "Quantidade": item["Qtd Chapas"],
                    "Tempo Total": item["Tempo Total"]
                })
            st.success(f"Trabalho enviado para {maquina_escolhida}")

# =====================
# Painel Principal - Máquinas
# =====================
st.markdown("---")
cols = st.columns(1)

for i, maquina in enumerate(MAQUINAS):
    with cols[i % 1]:
        st.markdown(f"## 🔧 {maquina}")

        corte = st.session_state.corte_atual.get(maquina)
        fila = st.session_state.fila_maquinas.get(maquina, [])

        # Mostrar corte atual
        if corte:
            st.markdown(
                f"**🔹 Corte Atual:** {corte['Proposta']} | CNC {corte['CNC']} | "
                f"{corte['Material']} | {corte['Espessura']} mm"
            )
            if st.button("✅ Finalizar Corte Atual", key=f"fim_{maquina}"):
                st.session_state.corte_atual[maquina] = None
                st.success("Corte finalizado")
        else:
            st.markdown("_Nenhum corte em andamento_")

        # Mostrar fila
        if fila:
            st.markdown("### 📋 Fila de Espera")
            df = pd.DataFrame(fila)
            st.dataframe(df, use_container_width=True, hide_index=True)

            opcoes = [f"{item['Proposta']} | CNC {item['CNC']}" for item in fila]
            escolha = st.selectbox("Escolha próximo CNC:", opcoes, key=f"escolha_{maquina}")
            if st.button("▶️ Iniciar Corte", key=f"iniciar_{maquina}"):
                index = opcoes.index(escolha)
                st.session_state.corte_atual[maquina] = fila.pop(index)
                st.success("Corte iniciado")
                st.rerun()
        else:
            st.markdown("_Fila vazia_")
