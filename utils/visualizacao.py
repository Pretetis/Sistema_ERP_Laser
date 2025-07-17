from pathlib import Path
from pdf2image import convert_from_path
import streamlit as st

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

    return imagem_destino