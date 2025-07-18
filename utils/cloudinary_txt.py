import cloudinary
import cloudinary.uploader
import cloudinary.api
from pathlib import Path
import requests
from io import BytesIO

# Configure Cloudinary (você já usa isso em visualizacao2.py)
cloudinary.config(
    cloud_name="dm6vke2eo",
    api_key="231723737594549",
    api_secret="eZdQ3p0dq5sNDs_zidUhQgcwhZM"
)

def enviar_txt_cloudinary(conteudo_txt: str, nome_arquivo: str, pasta="txt_trabalhos"):
    try:
        public_id = f"{pasta}/{nome_arquivo}".replace(".txt", "")
        arquivo = BytesIO(conteudo_txt.encode('utf-8'))
        arquivo.name = nome_arquivo  # Garante que o Cloudinary saiba que é .txt

        response = cloudinary.uploader.upload(
            file=arquivo,
            resource_type="raw",
            public_id=public_id,
            overwrite=True,
        )
        return response["secure_url"]
    except Exception as e:
        print("Erro ao enviar TXT:", e)
        return None

def baixar_txt_cloudinary(nome_arquivo: str, destino: Path, pasta="txt_trabalhos"):
    nome_arquivo = nome_arquivo.replace(".txt", "") + ".txt"
    url = f"https://res.cloudinary.com/{cloudinary.config().cloud_name}/raw/upload/{pasta}/{nome_arquivo}"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            destino.write_bytes(r.content)
            return True
    except Exception as e:
        print("Erro ao baixar TXT:", e)
    return False

def listar_txts_cloudinary(pasta="txt_trabalhos") -> list[str]:
    arquivos = []
    try:
        res = cloudinary.api.resources(
            type="upload",
            resource_type="raw",
            prefix=f"{pasta}/",
            max_results=100
        )
        for item in res.get("resources", []):
            nome = item["public_id"].split("/")[-1] + ".txt"
            arquivos.append(nome)
    except Exception as e:
        print("Erro ao listar arquivos do Cloudinary:", e)
    return arquivos

def deletar_txt_cloudinary(nome_arquivo: str, pasta="txt_trabalhos"):
    public_id = f"{pasta}/{nome_arquivo}".replace(".txt", "")
    try:
        cloudinary.api.delete_resources([public_id], resource_type="raw")
        return True
    except Exception as e:
        print("Erro ao deletar TXT:", e)
        return False
    
def baixar_txt_cloudinary_conteudo(nome_arquivo: str, pasta="txt_trabalhos"):
    url = f"https://res.cloudinary.com/{cloudinary.config().cloud_name}/raw/upload/{pasta}/{nome_arquivo.replace('.txt','')}.txt"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print("Erro ao baixar TXT:", e)
    return ""