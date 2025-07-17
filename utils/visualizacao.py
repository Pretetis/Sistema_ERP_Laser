from pathlib import Path
from pdf2image import convert_from_path
import cloudinary
import cloudinary.uploader
import streamlit as st

# Configuração do Cloudinary
cloudinary.config(
    cloud_name="dm6vke2eo",
    api_key="231723737594549",
    api_secret="eZdQ3p0dq5sNDs_zidUhQgcwhZM"
)

def gerar_preview_pdf(pdf_path, pasta_destino="previews"):
    pdf_path = Path(pdf_path)
    pasta = Path(pasta_destino)
    pasta.mkdir(exist_ok=True)

    imagem_destino = pasta / f"{pdf_path.stem}.png"

    if not imagem_destino.exists():
        try:
            imagens = convert_from_path(str(pdf_path), first_page=1, last_page=1, dpi=100)
            imagens[0].save(imagem_destino, "PNG")
        except Exception as e:
            st.error(f"Erro ao gerar imagem para {pdf_path.name}")
            st.exception(e)
            return None

    # Upload da imagem para o Cloudinary
    try:
        response = cloudinary.uploader.upload(
            str(imagem_destino),
            folder="previews_pdf",  # pasta no Cloudinary (opcional)
            public_id=pdf_path.stem,  # nome da imagem (sem extensão)
            overwrite=True,
            resource_type="image"
        )
        return response["secure_url"]  # URL HTTPS da imagem
    except Exception as e:
        st.error("Erro ao enviar imagem ao Cloudinary")
        st.exception(e)
        return None
