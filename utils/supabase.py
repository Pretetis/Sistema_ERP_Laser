from supabase import create_client, Client
from pathlib import Path
from urllib.parse import urlparse
import streamlit as st
import pandas as pd
from io import BytesIO
from PIL import Image
from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Cria o cliente
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "erpmicrons"

usuario = st.session_state.get("usuario", {}).get("username", "desconhecido")

def arquivo_existe(nome_arquivo: str) -> bool:
    partes = nome_arquivo.split("/")
    pasta = "/".join(partes[:-1])  # pasta onde o arquivo deve estar
    nome = partes[-1]
    if not pasta:
        pasta = ""  # ou None, dependendo do que a API aceita

    arquivos = supabase.storage.from_(BUCKET_NAME).list(path=pasta)
    existe = any(arq["name"] == nome for arq in arquivos)
    return existe

def deletar_arquivo_supabase(nome_arquivo: str) -> bool:
    if not arquivo_existe(nome_arquivo):
        print(f"Arquivo '{nome_arquivo}' não existente.")
        return False
    try:
        supabase.storage.from_(BUCKET_NAME).remove([nome_arquivo])
        print(f"Arquivo '{nome_arquivo}' excluído com sucesso.")
        return True
    except Exception as e:
        print(f"Erro ao tentar excluir o arquivo '{nome_arquivo}': {e}")
        return False

def upload_imagem_to_supabase(path_imagem: Path, destino: str = "aguardando_aprovacao") -> str:
    destino_final = f"{destino}/{path_imagem.name}"

    # Upload da imagem
    with path_imagem.open("rb") as f:
        supabase.storage.from_(BUCKET_NAME).upload(
            destino_final,
            f,
            file_options={"content-type": "image/png"}
        )

    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{destino_final}"

def upload_imagem_memoria_to_supabase(imagem_pil: Image.Image, nome: str, destino: str = "previews") -> str:
    buffer = BytesIO()
    imagem_pil.save(buffer, format="PNG")
    buffer.seek(0)

    nome_arquivo = f"{nome}.png"
    destino_final = f"{destino}/{nome_arquivo}"

    supabase.storage.from_(BUCKET_NAME).upload(
        destino_final,
        buffer,
        file_options={"content-type": "image/png"}
    )

    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{destino_final}"

def excluir_imagem_supabase(link_completo: str) -> bool:
    try:
        # Extrai o caminho do objeto dentro do bucket
        path = urlparse(link_completo).path
        path_relativo = path.split(f"/{BUCKET_NAME}/")[-1]  # ex: previews/1543.png

        resposta = supabase.storage.from_(BUCKET_NAME).remove([path_relativo])
        
        if resposta.get("error"):
            print("Erro ao excluir:", resposta["error"])
            return False

        return True

    except Exception as e:
        print(f"Erro ao tentar excluir imagem: {e}")
        return False
    
# Baixar e salvar no disco
def baixar_txt_para_disco(nome_arquivo: str, destino: Path) -> bool:
    try:
        conteudo = supabase.storage.from_(BUCKET_NAME).download(nome_arquivo)
        destino.write_bytes(conteudo)
        return True
    except Exception:
        return False

import pandas as pd
import streamlit as st
from utils.supabase import supabase

def historico_por_maquina():
    dados = supabase.table("historico_alteracoes")\
        .select("*")\
        .eq("tabela_afetada", "corte_atual")\
        .order("timestamp", desc=False)\
        .execute().data

    registros = []
    for row in dados:
        antes = row["dados_antes"] or {}
        depois = row["dados_depois"] or {}
        evento = "Alteração"

        if row["tipo_operacao"] == "INSERT":
            evento = "Corte Iniciado"
        elif row["tipo_operacao"] == "UPDATE":
            if antes.get("qtd_chapas") and depois.get("qtd_chapas"):
                if depois["qtd_chapas"] < antes["qtd_chapas"]:
                    evento = "Chapa Finalizada"
                else:
                    evento = "Alteração Manual"
            else:
                evento = "Atualização"
        elif row["tipo_operacao"] == "DELETE":
            if antes.get("qtd_chapas", 1) > 1:
                evento = "Corte Cancelado"
            else:
                evento = "Corte Finalizado"

        registros.append({
            "Máquina": depois.get("maquina") or antes.get("maquina"),
            "Evento": evento,
            "Proposta": depois.get("proposta") or antes.get("proposta"),
            "CNC": depois.get("cnc") or antes.get("cnc"),
            "Qtd Chapas": depois.get("qtd_chapas") or antes.get("qtd_chapas"),
            "Por": row["modificado_por"],
            "Quando": formatar_data_brasilia(row["timestamp"])
        })

    df = pd.DataFrame(registros)

    if df.empty:
        st.info("Nenhum histórico encontrado.")
        return

    maquinas = df["Máquina"].dropna().unique()

    for maquina in sorted(maquinas):
        st.subheader(f"🖥️ {maquina}")
        df_maquina = df[df["Máquina"] == maquina].sort_values("Quando", ascending=False)
        st.dataframe(df_maquina, use_container_width=True)

def formatar_data_brasilia(timestamp_str):
    dt_utc = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    dt_brasilia = dt_utc.astimezone(ZoneInfo("America/Sao_Paulo"))
    return dt_brasilia.strftime("%d/%m/%Y %H:%M:%S")

def historico_envios_para_laser():
    dados = supabase.table("historico_alteracoes")\
        .select("*")\
        .eq("tabela_afetada", "fila_maquinas")\
        .eq("tipo_operacao", "INSERT")\
        .order("timestamp", desc=False)\
        .execute().data

    registros = []
    for row in dados:
        info = row["dados_depois"] or {}
        registros.append({
            "Máquina": info.get("maquina"),
            "CNC": info.get("cnc"),
            "Proposta": info.get("proposta"),
            "Material": info.get("material"),
            "Espessura": info.get("espessura"),
            "Qtd Chapas": info.get("qtd_chapas"),
            "Tempo": info.get("tempo_total"),
            "Por": row["modificado_por"],
            "Quando": formatar_data_brasilia(row["timestamp"])
        })

    df = pd.DataFrame(registros).sort_values("Quando", ascending=False)
    st.dataframe(df, use_container_width=True)

def historico_autorizacoes():
    dados = supabase.table("historico_alteracoes")\
        .select("*")\
        .eq("tabela_afetada", "trabalhos_pendentes")\
        .eq("tipo_operacao", "UPDATE")\
        .order("timestamp", desc=False)\
        .execute().data

    autorizados = []
    for row in dados:
        antes = row["dados_antes"] or {}
        depois = row["dados_depois"] or {}
        if not antes.get("autorizado") and depois.get("autorizado"):
            autorizados.append({
                "CNC": depois.get("cnc"),
                "Proposta": depois.get("proposta"),
                "Material": depois.get("material"),
                "Espessura": depois.get("espessura"),
                "Por": row["modificado_por"],
                "Quando": formatar_data_brasilia(row["timestamp"])
            })

    df = pd.DataFrame(autorizados).sort_values("Quando", ascending=False)
    st.dataframe(df, use_container_width=True)