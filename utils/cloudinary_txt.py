import cloudinary
import cloudinary.uploader
import cloudinary.api
from pathlib import Path
import requests

# Configure Cloudinary (você já usa isso em visualizacao2.py)
cloudinary.config(
    cloud_name="dm6vke2eo",
    api_key="231723737594549",
    api_secret="eZdQ3p0dq5sNDs_zidUhQgcwhZM"
)

def enviar_txt_cloudinary(caminho: Path, pasta="txt_trabalhos"):
    if not caminho.exists():
        return None

    try:
        response = cloudinary.uploader.upload(
            str(caminho),
            folder=pasta,
            public_id=caminho.stem,
            resource_type="raw",
            overwrite=True
        )
        return response["secure_url"]
    except Exception as e:
        print("Erro ao enviar TXT:", e)
        return None

def baixar_txt_cloudinary(nome_arquivo: str, destino: Path, pasta="txt_trabalhos"):
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
            max_results=100  # pode ajustar se tiver muitos arquivos
        )
        for item in res.get("resources", []):
            nome = item["public_id"].split("/")[-1]  # remove o prefixo da pasta
            arquivos.append(nome)
    except Exception as e:
        print("Erro ao listar arquivos do Cloudinary:", e)
    return arquivos
