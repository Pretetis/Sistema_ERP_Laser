import streamlit as st
import pandas as pd
import plotly.express as px

from utils.auth import verificar_autenticacao
verificar_autenticacao()

from utils.storage import supabase

st.set_page_config(page_title="Dashboard", layout="wide")

@st.cache_data(ttl=300)
def carregar_eventos():
    response = supabase.table("eventos_corte").select("*").execute()
    df = pd.DataFrame(response.data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

def classificar_transicao(prev_tipo, atual_tipo):
    if prev_tipo in ["iniciado", "retomado"] and atual_tipo in ["parado", "cancelado"]:
        return "Tempo de Corte"
    elif prev_tipo in ["chapa_finalizada", "cancelado"] and atual_tipo == "iniciado":
        return "Tempo Parado"
    elif prev_tipo == "parado" and atual_tipo in ["retomado", "cancelado"]:
        return "Tempo Interrompido"
    else:
        return None

def calcular_tempos_personalizados(df_eventos):
    resultados = []

    for maquina in df_eventos["maquina"].unique():
        df_maquina = df_eventos[df_eventos["maquina"] == maquina].sort_values("timestamp").reset_index(drop=True)
        
        for i in range(len(df_maquina) - 1):
            atual = df_maquina.iloc[i]
            proximo = df_maquina.iloc[i + 1]

            tipo = classificar_transicao(atual["tipo_evento"], proximo["tipo_evento"])
            if tipo:
                delta = proximo["timestamp"] - atual["timestamp"]
                if delta.total_seconds() < 0 or delta.total_seconds() > 12 * 3600:  # ignora tempos negativos ou longos demais
                    continue
                resultados.append({
                    "maquina": maquina,
                    "tipo_tempo": tipo,
                    "minutos": delta.total_seconds() / 60
                })

    return pd.DataFrame(resultados)

def grafico_barras_resumo(df_tempos, maquina):
    df_maquina = df_tempos[df_tempos["maquina"] == maquina]
    resumo = df_maquina.groupby("tipo_tempo")["minutos"].sum().reset_index()
    resumo["horas"] = resumo["minutos"] / 60

    cores_personalizadas = {
        "Tempo de Corte": "green",
        "Tempo Parado": "gold",
        "Tempo Interrompido": "red"
    }

    fig = px.bar(
        resumo,
        x="tipo_tempo",
        y="horas",
        color="tipo_tempo",
        title=f"Resumo de Tempos (Horas) - {maquina}",
        labels={"tipo_tempo": "Tipo de Tempo", "horas": "Horas"},
        color_discrete_map=cores_personalizadas,
        category_orders={"tipo_tempo": ["Tempo de Corte", "Tempo Parado", "Tempo Interrompido"]}
    )

    # Adiciona animação leve no layout
    fig.update_layout(
        transition=dict(
            duration=700,
            easing='cubic-in-out'
        )
    )

    return fig

def grafico_pizza_motivos(df_eventos, maquina):
    df_parado = df_eventos[
        (df_eventos["maquina"] == maquina) &
        (df_eventos["tipo_evento"] == "parado")
    ]
    if df_parado.empty:
        return None
    
    df_motivos = df_parado["motivo"].fillna("Desconhecido")
    contagem = df_motivos.value_counts().reset_index()
    contagem.columns = ["motivo", "frequencia"]

    fig = px.pie(
        contagem,
        names="motivo",
        values="frequencia",
        title="Motivos de Interrupção",
        color_discrete_sequence=px.colors.sequential.Reds
    )
    return fig
# Main
st.title("Dashboard de Análise de Eventos por Máquina")

df_eventos = carregar_eventos()
df_tempos = calcular_tempos_personalizados(df_eventos)
maquinas = sorted(df_eventos["maquina"].dropna().unique())

for maquina in maquinas:
    with st.container(border=True):
        st.subheader(maquina)
        col1, col2 = st.columns([2, 1])

        with col1:
            fig_barras = grafico_barras_resumo(df_tempos, maquina)
            st.plotly_chart(fig_barras, use_container_width=True)

        with col2:
            fig_pizza = grafico_pizza_motivos(df_eventos, maquina)
            if fig_pizza:
                st.plotly_chart(fig_pizza, use_container_width=True)
            else:
                st.info("Sem motivos de interrupção registrados.")
