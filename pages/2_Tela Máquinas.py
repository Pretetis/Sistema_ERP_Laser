import streamlit as st
from streamlit_autorefresh import st_autorefresh
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, timezone

# Auto-refresh a cada 100 segundos
st_autorefresh(interval=100000, key="refresh")

st.set_page_config(layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Escolher turno aqui
tipo_turno_atual = 2  # 👈 Altere para 1, 2 ou 3

maquinas = [f"LASER {i}" for i in range(1, 7)]
nomes_exibicao = [f"LASER {i}" for i in range(1, 7)]

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

def calcular_fim_previsto(inicio: datetime, duracao: timedelta, tipo_turno: int) -> datetime:
    restante = duracao
    atual = inicio

    while restante.total_seconds() > 0:
        if tipo_turno == 1:
            return atual + restante

        elif tipo_turno == 2:
            turno_inicio = atual.replace(hour=6, minute=0, second=0, microsecond=0)
            turno_fim = atual.replace(hour=17, minute=33, second=0, microsecond=0)

        elif tipo_turno == 3:
            if atual.hour >= 21:
                turno_inicio = atual.replace(hour=21, minute=0, second=0, microsecond=0)
                turno_fim = (atual + timedelta(days=1)).replace(hour=15, minute=48, second=0, microsecond=0)
            elif atual.hour < 15 or (atual.hour == 15 and atual.minute < 48):
                turno_inicio = atual.replace(hour=21, minute=0, second=0, microsecond=0) - timedelta(days=1)
                turno_fim = atual.replace(hour=15, minute=48, second=0, microsecond=0)
            else:
                atual = atual.replace(hour=21, minute=0, second=0, microsecond=0)
                continue
        else:
            return atual + restante

        if atual < turno_inicio:
            atual = turno_inicio

        if atual >= turno_fim:
            atual = turno_inicio + timedelta(days=1)
            continue

        tempo_disponivel = turno_fim - atual
        if restante <= tempo_disponivel:
            return atual + restante
        else:
            restante -= tempo_disponivel
            atual = turno_inicio + timedelta(days=1)

    return atual

# Divide em duas linhas de 3 colunas
linhas = [maquinas[:3], maquinas[3:]]
nomes_linhas = [nomes_exibicao[:3], nomes_exibicao[3:]]

# Lista para alimentar a tabela final
dados_turno = []

for linha_maquinas, linha_nomes in zip(linhas, nomes_linhas):
    cols = st.columns(3)
    for col, maquina, nome_exibicao in zip(cols, linha_maquinas, linha_nomes):
        with col:
            st.markdown(f"<h3 style='text-align:center'>{nome_exibicao}</h3>", unsafe_allow_html=True)

            corte = supabase.table("corte_atual").select("*").eq("maquina", maquina).execute()
            corte_data = corte.data[0] if corte.data else None

            with st.container(border=True, height=400):
                if corte_data:
                    tempo_str = corte_data.get("tempo_total", "00:00:00")
                    try:
                        h, m, s = map(int, tempo_str.split(":"))
                        tempo_duracao = timedelta(hours=h, minutes=m, seconds=s)
                    except:
                        tempo_duracao = timedelta()

                    inicio_str = corte_data.get("inicio")
                    try:
                        inicio = datetime.fromisoformat(inicio_str)
                    except:
                        inicio = datetime.now()

                    fim_previsto = calcular_fim_previsto(inicio, tempo_duracao, tipo_turno_atual)
                    fim_previsto_str = fim_previsto.strftime("%d/%m %H:%M")

                    # Adiciona aos dados da tabela
                    dados_turno.append({
                        "Máquina": maquina,
                        "Proposta": corte_data.get("proposta"),
                        "Material": corte_data.get("material"),
                        "Espessura (mm)": corte_data.get("espessura"),
                        "Qtd Chapas": corte_data.get("qtd_chapas"),
                        "Fim Previsto": fim_previsto_str
                    })

                    st.markdown("### 🟢 Cortando agora")
                    st.markdown(
                        f"<div class='big-text'>📌 {corte_data.get('proposta')} | 📄 CNC: {corte_data.get('cnc')} | "
                        f"🧪 {corte_data.get('material')} | Esp: {corte_data.get('espessura')} mm<br>"
                        f"📦 x{corte_data.get('qtd_chapas')} | ⏱️ Fim Previsto: {fim_previsto_str}</div>",
                        unsafe_allow_html=True
                    )
                    # Cálculo de progresso
                    fuso_brasil = timezone(timedelta(hours=-3))
                    agora = datetime.now(fuso_brasil)

                    if inicio.tzinfo is None:
                        inicio = inicio.replace(tzinfo=fuso_brasil)

                    if tempo_duracao.total_seconds() > 0:
                        progresso = (agora - inicio).total_seconds() / tempo_duracao.total_seconds()
                        progresso = max(0, min(progresso, 0.9999 if progresso >= 1 else progresso))
                    else:
                        progresso = 0.0

                    texto_barra = "100% concluído" if progresso >= 0.9999 else f"{int(progresso * 100)}% concluído"
                    st.progress(progresso, text=texto_barra)
                else:
                    st.markdown("### 🔴 Nenhum corte em andamento")

                st.divider()

                st.markdown("### 🟡 Na fila")
                fila = supabase.table("fila_maquinas").select("*").eq("maquina", maquina).execute()
                fila_df = pd.DataFrame(fila.data)

                if not fila_df.empty:
                    for _, row in fila_df.iterrows():
                        st.markdown(
                            f"<div class='big-text'>- {row.get('proposta')} | {row.get('material')} | "
                            f"{row.get('espessura')} mm | CNC: {row.get('cnc')} | x{row.get('qtd_chapas')} | "
                            f"⏱️ {row.get('tempo_total')}</div>",
                            unsafe_allow_html=True
                        )
                else:
                    st.markdown("<div class='big-text'>Sem trabalhos na fila.</div>", unsafe_allow_html=True)
