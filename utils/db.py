from utils.supabase import supabase

import plotly.graph_objects as go
import pandas as pd
import streamlit as st
import pytz
import uuid

from datetime import datetime, timedelta
from pytz import timezone
from dateutil import parser

def inserir_trabalho_pendente(dados):
    usuario = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    dados["modificado_por"] = usuario
    supabase.table("trabalhos_pendentes").insert(dados).execute()

def adicionar_na_fila(maquina, trabalho, modificado_por="desconhecido"):
    nome = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    supabase.table("fila_maquinas").insert({
        "maquina": maquina,
        "proposta": trabalho["proposta"],
        "cnc": trabalho["cnc"],
        "material": trabalho["material"],
        "espessura": trabalho["espessura"],
        "qtd_chapas": int(trabalho["qtd_chapas"]),
        "tempo_total": trabalho["tempo_total"],
        "caminho": trabalho.get("caminho", ""),
        "programador": trabalho["programador"],
        "processos": normalizar_processos(trabalho.get("processos")),
        "gas": trabalho.get("gas", None),
        "data_prevista": trabalho.get("data_prevista"),
        "modificado_por": nome,
    }).execute()

def obter_fila(maquina):
    res = supabase.table("fila_maquinas")\
        .select("*")\
        .eq("maquina", maquina)\
        .order("posicao", desc=False)\
        .execute()
    return res.data if res.data else []

def cnc_ja_existe(cnc: str) -> bool:
    res = supabase.table("trabalhos_pendentes")\
        .select("cnc")\
        .eq("cnc", cnc)\
        .execute()
    return len(res.data) > 0

def excluir_trabalho_por_cnc(cnc: str):
    supabase.table("trabalhos_pendentes").delete().eq("cnc", cnc).execute()

def obter_corte_atual(maquina):
    res = supabase.table("corte_atual").select("*").eq("maquina", maquina).execute()
    return res.data[0] if res.data else None


def iniciar_corte(maquina, id_fila):
    nome = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    fuso_sp = pytz.timezone("America/Sao_Paulo")
    agora = datetime.now(fuso_sp).isoformat()

    fila = supabase.table("fila_maquinas").select("*").eq("id", id_fila).execute()
    if not fila.data:
        return

    item = fila.data[0]

    supabase.table("fila_maquinas").delete().eq("id", id_fila).execute()

    supabase.table("corte_atual").upsert({
        "maquina": item["maquina"],
        "proposta": item["proposta"],
        "cnc": item["cnc"],
        "material": item["material"],
        "espessura": item["espessura"],
        "qtd_chapas": int(item["qtd_chapas"]),
        "tempo_total": item["tempo_total"],
        "caminho": item["caminho"],
        "programador": item["programador"],
        "processos": item.get("processos"),
        "gas": item.get("gas", None),
        "data_prevista": item["data_prevista"],
        "inicio": agora,
        "modificado_por": nome,
    }).execute()

    registrar_evento(maquina, "iniciado", item["proposta"], item["cnc"], nome=nome)

def finalizar_corte(maquina, nome):
    atual = obter_corte_atual(maquina)
    if not atual:
        return

    qtd_chapas = atual["qtd_chapas"]
    if qtd_chapas <= 0:
        excluir_do_corte(maquina)
        return

    tempo_total_str = atual["tempo_total"]
    h, m, s = map(int, tempo_total_str.split(":"))
    tempo_total = timedelta(hours=h, minutes=m, seconds=s)

    tempo_por_chapa = tempo_total / qtd_chapas
    novo_qtd_chapas = qtd_chapas - 1

    if novo_qtd_chapas > 0:
        novo_tempo = tempo_por_chapa * novo_qtd_chapas
        novo_tempo_str = timedelta_to_hms_string(novo_tempo)

        supabase.table("corte_atual").update({
            "qtd_chapas": novo_qtd_chapas,
            "tempo_total": novo_tempo_str,
            "modificado_por": nome,
        }).eq("maquina", maquina).execute()

        registrar_evento(maquina, "chapa_finalizada", atual["proposta"], atual["cnc"], nome=nome)

    else:
        excluir_do_corte(maquina)
        registrar_evento(maquina, "finalizado", atual["proposta"], atual["cnc"], nome=nome)


def excluir_da_fila(maquina, id_trabalho):
    supabase.table("fila_maquinas").delete().eq("maquina", maquina).eq("id", id_trabalho).execute()


def excluir_do_corte(maquina):
    supabase.table("corte_atual").delete().eq("maquina", maquina).execute()

def retornar_para_pendentes(maquina):
    atual = obter_corte_atual(maquina)
    if not atual:
        return

    grupo = f"{atual['proposta']}-{int(atual['espessura'] * 100):04}-{atual['material']}"

    trabalho = {
        "grupo": grupo,
        "proposta": atual["proposta"],
        "cnc": atual["cnc"],
        "material": atual["material"],
        "espessura": atual["espessura"],
        "qtd_chapas": int(atual["qtd_chapas"]),
        "tempo_total": atual["tempo_total"],
        "programador": atual.get("programador", "DESCONHECIDO"),
        "data_prevista": atual["data_prevista"],
        "processos": normalizar_processos(atual.get("processos")),
        "autorizado": True,
        "caminho": atual.get("caminho", f"CNC/{atual['cnc']}.pdf"),
        "gas": atual.get("gas", None)
    }

    inserir_trabalho_pendente(trabalho)
    excluir_do_corte(maquina)

    registrar_evento(maquina, "cancelado", atual["proposta"], atual["cnc"])

def retornar_item_da_fila_para_pendentes(id_trabalho):
    nome = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    res = supabase.table("fila_maquinas").select("*").eq("id", id_trabalho).execute()
    if not res.data:
        return

    item = res.data[0]
    grupo = f"{item['proposta']}-{int(item['espessura'] * 100):04}-{item['material']}"

    novo_trabalho = {
        "grupo": grupo,
        "proposta": item["proposta"],
        "cnc": item["cnc"],
        "material": item["material"],
        "espessura": item["espessura"],
        "qtd_chapas": int(item["qtd_chapas"]),
        "tempo_total": item["tempo_total"],
        "programador": item.get("programador", "DESCONHECIDO"),
        "data_prevista": item["data_prevista"],
        "processos": normalizar_processos(item.get("processos")),
        "autorizado": True,
        "caminho": item.get("caminho"," "),
        "gas": item.get("gas", None),
        "modificado_por": nome,
    }

    inserir_trabalho_pendente(novo_trabalho)
    registrar_evento(item["maquina"], "retornado", item["proposta"], item["cnc"], nome=nome)
    excluir_da_fila(item["maquina"], id_trabalho)


def atualizar_quantidade(maquina, nova_quantidade):
    nome = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    supabase.table("corte_atual").update({
        "qtd_chapas": nova_quantidade,
        "modificado_por": nome,
    }).eq("maquina", maquina).execute()



def atualizar_trabalho_pendente(cnc, grupo, tempo_total, data_prevista=None, processos=None, autorizado=False, gas=None):
    nome = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    update_data = {
        "tempo_total": tempo_total,
        "data_prevista": data_prevista,
        "processos": processos,
        "autorizado": autorizado,
        "gas": gas,
        "modificado_por": nome,
    }

    # Remove campos nulos para evitar sobrescrita
    update_data = {k: v for k, v in update_data.items() if v is not None}

    supabase.table("trabalhos_pendentes")\
        .update(update_data)\
        .eq("grupo", grupo)\
        .eq("cnc", cnc)\
        .execute()

def excluir_trabalhos_grupo(grupo: str):
    nome = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    registrar_evento(
        maquina="N/A",  
        tipo_evento="excluido",
        proposta=grupo.split("-")[0],  # ajuste conforme necessário
        cnc="N/A",
        motivo="Exclusão manual pelo usuário",
        nome=nome
    )

    supabase.table("trabalhos_pendentes").delete().eq("grupo", grupo).execute()

    
def timedelta_to_hms_string(td):
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def normalizar_processos(val):
    if isinstance(val, list) and val:
        return val
    return ["Corte Retornado"]

def retomar_interrupcao(maquina):
    nome = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    res = supabase.table("eventos_corte")\
        .select("*")\
        .eq("maquina", maquina)\
        .eq("tipo_evento", "parado")\
        .is_("tempo_total", None)\
        .order("timestamp", desc=True)\
        .limit(1)\
        .execute()

    if res.data:
        parada = res.data[0]

        # Converte a string para datetime aware
        inicio = parser.isoparse(parada["timestamp"])
        fim = datetime.now(timezone("America/Sao_Paulo"))

        # Garante que ambos são aware
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone("America/Sao_Paulo"))

        duracao = fim - inicio

        registrar_evento(
            maquina,
            "retomado",
            parada["proposta"],
            parada["cnc"],
            tempo_total=str(duracao),
            nome = nome
        )

def registrar_evento(maquina, tipo_evento, proposta, cnc, motivo=None, tempo_total=None, nome=None):
    if not nome:
        nome = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    supabase.table("eventos_corte").insert({
        "maquina": maquina,
        "proposta": proposta,
        "cnc": cnc,
        "tipo_evento": tipo_evento,
        "timestamp": datetime.now().isoformat(),
        "motivo": motivo,
        "tempo_total": tempo_total,
        "modificado_por": nome,
    }).execute()
def obter_eventos_corte(maquina):
    try:
        res = supabase.table("eventos_corte")\
            .select("*")\
            .eq("maquina", maquina)\
            .order("timestamp", desc=False)\
            .execute()
        return res.data
    except Exception as e:
        st.error(f"Erro ao obter eventos da máquina {maquina}: {e}")
        return []

def mostrar_grafico_eventos(maquina, modo="individual"):
    eventos = obter_eventos_corte(maquina)

    if not eventos:
        st.info("Sem eventos registrados para essa máquina.")
        return

    df = pd.DataFrame(eventos)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Mapeia os tipos de eventos em status numéricos
    df["status"] = df["tipo_evento"].map({
        "iniciado": 1,
        "retomado": 1,
        "chapa_finalizada": 1,
        "finalizado": 0,
        "cancelado": 0,
        "parado": -1
    }).fillna(method='ffill')

    df = df.sort_values("timestamp")

    df["hover_text"] = df.apply(
        lambda row: f"{row['tipo_evento'].upper()}<br>"
                    f"CNC: {row.get('cnc', '')}<br>"
                    f"Proposta: {row.get('proposta', '')}<br>"
                    f"Motivo: {row.get('motivo', '') if row['tipo_evento'] == 'parado' else ''}",
        axis=1
    )

    # Segmenta os dados por mudança de status
    segments = []
    current_color = df["status"].iloc[0]
    current_segment = [df.iloc[0]]

    for i in range(1, len(df)):
        if df["status"].iloc[i] != current_color:
            segments.append((current_color, pd.DataFrame(current_segment)))
            current_color = df["status"].iloc[i]
            current_segment = [df.iloc[i - 1], df.iloc[i]]
        else:
            current_segment.append(df.iloc[i])
    segments.append((current_color, pd.DataFrame(current_segment)))

    color_map = {
        -1: "red",
         0: "yellow",
         1: "green"
    }

    fig = go.Figure()

    for status_val, segment_df in segments:
        fig.add_trace(go.Scatter(
            x=segment_df["timestamp"],
            y=segment_df["status"],
            mode="lines+markers",
            line=dict(color=color_map.get(status_val, "gray"), width=3),
            marker=dict(size=6),
            text=segment_df["hover_text"],
            hoverinfo="text",
            line_shape="hv",
            showlegend=False  # 👈 remove da legenda
        ))

    for _, row in df[df["tipo_evento"] == "parado"].iterrows():
        fig.add_annotation(
            x=row["timestamp"],
            y=-1,
            text=row.get("motivo", "Sem motivo"),
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-30,
            bgcolor="black",
            font=dict(color="white", size=10)
        )

    fig.update_layout(
        title=f"Atividade da Máquina: {maquina}",
        xaxis_title="Horário",
        yaxis=dict(
            tickvals=[-1, 0, 1],
            ticktext=["Interrompido", "Parado", "Funcionando"],
            range=[-1.5, 1.5]
        ),
        yaxis_title="Status",
        showlegend=False,  # 👈 desativa legenda do gráfico
        height=300
    )

    key_base = f"{modo}_{maquina.replace(' ', '_')}"

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"grafico_{maquina}_{uuid.uuid4()}"
    )

def obter_status_interrompido(maquina: str):
    result = supabase.table("corte_atual").select("interrompido").eq("maquina", maquina).execute()
    data = result.data
    return data[0]["interrompido"] if data else False

def atualizar_status_interrompido(maquina: str, interrompido: bool):
    supabase.table("corte_atual").update({"interrompido": interrompido}).eq("maquina", maquina).execute()

def obter_todos_cortes_atuais():
    res = supabase.table("corte_atual").select("*").execute()
    return {r["maquina"]: r for r in res.data} if res.data else {}
def obter_todas_filas():
    res = supabase.table("fila_maquinas").select("*").order("posicao").execute()
    filas = {}
    for item in res.data or []:
        filas.setdefault(item["maquina"], []).append(item)
    return filas