from supabase import create_client, Client
from pathlib import Path
from dotenv import load_dotenv
import os
import time
import tempfile
import io

# Carrega as variáveis do .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Cria o cliente
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "erpmicrons"

'''
# Upload de arquivo .txt para subpastas (ex: aguardando_aprovacao/)
def upload_txt_to_supabase(nome_arquivo: str, conteudo: str, pasta: str = "aguardando_aprovacao") -> str:
    # Cria arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp_file:
        tmp_file.write(conteudo)
        caminho_temp = Path(tmp_file.name)

    # Caminho completo no bucket
    caminho_bucket = f"{pasta}/{nome_arquivo}"

    # Upload
    with caminho_temp.open("rb") as f:
        supabase.storage.from_(BUCKET_NAME).upload(
            caminho_bucket,
            f,
            file_options={"content-type": "text/plain"}
        )

    caminho_temp.unlink()  # Remove o arquivo temporário

    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{caminho_bucket}"
'''

def upload_txt_to_supabase(nome_arquivo: str, conteudo: str, pasta: str = "aguardando_aprovacao") -> str:
    caminho_bucket = f"{pasta}/{nome_arquivo}"

    # Cria arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp_file:
        tmp_file.write(conteudo)
        caminho_temp = Path(tmp_file.name)

    # Faz upload pelo caminho do arquivo físico
    supabase.storage.from_(BUCKET_NAME).upload(
        caminho_bucket,
        str(caminho_temp),
        file_options={"content-type": "text/plain"}
    )

    # Remove arquivo temporário
    caminho_temp.unlink()

    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{caminho_bucket}"

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

    # Remove imagem anterior se existir
    deletar_arquivo_supabase(destino_final)

    # Aguarda até a exclusão se concretizar
    for _ in range(3):
        if not arquivo_existe(destino_final):
            break
        time.sleep(1)
    else:
        raise Exception(f"O arquivo '{destino_final}' ainda existe após remoção. Upload cancelado.")

    # Upload da imagem
    with path_imagem.open("rb") as f:
        supabase.storage.from_(BUCKET_NAME).upload(
            destino_final,
            f,
            file_options={"content-type": "image/png"}
        )

    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{destino_final}"

# Listar arquivos .txt de uma pasta específica
def listar_txts_supabase(pasta: str = "aguardando_aprovacao") -> list[str]:
    arquivos = supabase.storage.from_(BUCKET_NAME).list(path=pasta)
    return [f"{pasta}/{f['name']}" for f in arquivos if f['name'].endswith(".txt")]

# Baixar conteúdo do .txt
def baixar_txt_conteudo(nome_arquivo: str) -> str:
    response = supabase.storage.from_(BUCKET_NAME).download(nome_arquivo)
    return response.decode("utf-8")

# Baixar e salvar no disco
def baixar_txt_para_disco(nome_arquivo: str, destino: Path) -> bool:
    try:
        conteudo = supabase.storage.from_(BUCKET_NAME).download(nome_arquivo)
        destino.write_bytes(conteudo)
        return True
    except Exception:
        return False
