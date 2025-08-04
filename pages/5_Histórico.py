import streamlit as st

from utils.auth import verificar_autenticacao
verificar_autenticacao()

from utils.storage import historico_autorizacoes, historico_envios_para_laser, historico_por_maquina

st.set_page_config(page_title="Histórico", layout="wide")

#barra_navegacao()  # Exibe a barra no topo

aba1, aba2, aba3 = st.tabs(["📊 Histórico por Máquina", "🚀 Envios para LASER", "✅ Autorizações"])

with aba1:
    historico_por_maquina()

with aba2:
    historico_envios_para_laser()

with aba3:
    historico_autorizacoes()