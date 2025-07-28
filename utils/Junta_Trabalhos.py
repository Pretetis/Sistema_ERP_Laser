import pandas as pd
import streamlit as st
from utils.supabase import supabase

PREFIXOS_CATEGORIAS = {
    "aguardando_aprovacao": "aguardando_aprovacao",
    "trabalhos_pendentes": "trabalhos_pendentes"
}

def carregar_trabalhos():
    trabalhos = {
        "aguardando_aprovacao": [],
        "trabalhos_pendentes": []
    }

    res = supabase.table("trabalhos_pendentes").select("*").execute()
    registros = res.data if res.data else []
    df = pd.DataFrame(registros)

    if df.empty or "autorizado" not in df.columns:
        df_autorizado = pd.DataFrame()
        df_nao_autorizado = pd.DataFrame()
    else:
        df_autorizado = df[df["autorizado"] == True]
        df_nao_autorizado = df[df["autorizado"] != True]

    for status, df_base in [("aguardando_aprovacao", df_nao_autorizado), ("trabalhos_pendentes", df_autorizado)]:
        if df_base.empty:
            continue

        df_base["tempo_total"] = pd.to_timedelta(df_base["tempo_total"], errors="coerce")

        trabalhos_categoria = []
        for grupo_nome, subdf in df_base.groupby("grupo"):
            tempo_total = subdf["tempo_total"].dropna().sum()
            segundos = int(tempo_total.total_seconds())
            tempo_formatado = f"{segundos // 3600:02}:{(segundos % 3600) // 60:02}:{segundos % 60:02}"

            detalhes = subdf.copy()
            detalhes["tempo_total"] = detalhes["tempo_total"].apply(
                lambda x: (
                    f"{int(x.total_seconds()) // 3600:02}:"
                    f"{(int(x.total_seconds()) % 3600) // 60:02}:"
                    f"{int(x.total_seconds()) % 60:02}"
                ) if pd.notnull(x) else "00:00:00"
            )

            trabalho = {
                "grupo": grupo_nome,
                "proposta": subdf.iloc[0]["proposta"],
                "espessura": subdf.iloc[0]["espessura"],
                "material": subdf.iloc[0]["material"],
                "qtd_total": subdf["qtd_chapas"].sum(),
                "tempo_total": tempo_formatado,
                "detalhes": detalhes.to_dict(orient="records"),
                "data_prevista": subdf.iloc[0].get("data_prevista"),
                "processos": subdf.iloc[0].get("processos"),
            }

            trabalhos_categoria.append(trabalho)

        trabalhos[status] = trabalhos_categoria

    return trabalhos
