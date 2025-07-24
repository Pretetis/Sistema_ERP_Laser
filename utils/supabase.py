from supabase import create_client, Client
from pathlib import Path
from urllib.parse import urlparse
import streamlit as st
import time

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Cria o cliente
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "erpmicrons"

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

from io import BytesIO
from PIL import Image
from datetime import datetime

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
