import streamlit as st
from streamlit_autorefresh import st_autorefresh
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta

# Auto-refresh a cada 100 segundos
st_autorefresh(interval=100000, key="refresh")

# Layout da página full screen
st.set_page_config(layout="wide")

# Conexão Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Máquinas e nomes de exibição
maquinas = [f"LASER {i}" for i in range(1, 7)]
nomes_exibicao = [f"LASER {i}" for i in range(1, 7)]

# Estilo para texto maior e containers padronizados
st.markdown("""
    <style>
        .big-text {
            font-size: 20px;
        }
        .container-custom {
            min-height: 280px;
            padding: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Divide em duas linhas de 3 colunas
linhas = [maquinas[:3], maquinas[3:]]
nomes_linhas = [nomes_exibicao[:3], nomes_exibicao[3:]]

for linha_maquinas, linha_nomes in zip(linhas, nomes_linhas):
    cols = st.columns(3)
    for col, maquina, nome_exibicao in zip(cols, linha_maquinas, linha_nomes):
        with col:
            st.markdown(f"<h3 style='text-align:center'>{nome_exibicao}</h3>", unsafe_allow_html=True)

            corte = supabase.table("corte_atual").select("*").eq("maquina", maquina).execute()
            corte_data = corte.data[0] if corte.data else None

            # Obtém o tempo de corte e converte de string para timedelta
            tempo_str = corte_data.get("tempo_total", "00:00:00")
            try:
                h, m, s = map(int, tempo_str.split(":"))
                tempo_duracao = timedelta(hours=h, minutes=m, seconds=s)
            except:
                tempo_duracao = timedelta()

            # Tenta pegar o horário de início do corte; se não houver, usa agora
            inicio_str = corte_data.get("inicio")  # ex: "2025-07-24T08:00:00"
            try:
                inicio = datetime.fromisoformat(inicio_str)
            except:
                inicio = datetime.now()

            # Calcula o horário previsto de término
            fim_previsto = inicio + tempo_duracao
            fim_previsto_str = fim_previsto.strftime("%H:%M")

            with st.container(border=True, height=400):
                if corte_data:
                    st.markdown("### 🟢 Cortando agora")
                    st.markdown(
                        f"<div class='big-text'>📌 {corte_data.get('proposta')} | 📄 CNC: {corte_data.get('cnc')} | "
                        f"🧪 {corte_data.get('material')} | Esp: {corte_data.get('espessura')} mm<br>"
                        f"📦 x{corte_data.get('qtd_chapas')} | ⏱️ Previsto fim: {fim_previsto_str}</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown("### 🔴 Nenhum corte em andamento")

                st.divider()

                st.markdown("### 🟡 Na fila")
                fila = supabase.table("fila_maquinas").select("*").eq("maquina", maquina).execute()
                fila_df = pd.DataFrame(fila.data)

                if not fila_df.empty:
                    for _, row in fila_df.iterrows():
                        proposta = row.get('proposta', 'N/D')
                        material = row.get('material', 'N/D')
                        espessura = row.get('espessura', 'N/D')
                        cnc = row.get('cnc', 'N/D')
                        chapas = row.get('qtd_chapas', 'N/D')
                        tempo = row.get('tempo_total', 'N/D')
                        st.markdown(
                            f"<div class='big-text'>- {proposta} | {material} | {espessura} mm | "
                            f"CNC: {cnc} | x{chapas} | ⏱️ {tempo}</div>",
                            unsafe_allow_html=True
                        )
                else:
                    st.markdown("<div class='big-text'>Sem trabalhos na fila.</div>", unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)