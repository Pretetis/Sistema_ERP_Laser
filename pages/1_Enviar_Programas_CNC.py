import streamlit as st
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.extracao import extrair_dados_por_posicao
import shutil

# Caminho absoluto da pasta raiz (um nível acima de /pages)
RAIZ = Path(__file__).resolve().parent.parent

# Pastas de trabalho na raiz do projeto
PASTA_PDF = RAIZ / "CNC"
PASTA_TXT_PRONTOS = RAIZ / "Programas_Prontos"
PASTA_AUTORIZADOS = RAIZ / "autorizados"

# Garante que as pastas existam
PASTA_PDF.mkdir(exist_ok=True)
PASTA_TXT_PRONTOS.mkdir(exist_ok=True)
PASTA_AUTORIZADOS.mkdir(exist_ok=True)

st.set_page_config(page_title="Enviar Programas CNC", layout="wide")
st.title("📤 Enviar Programas CNC")

# 1. Upload dos PDFs
st.markdown("Faça o upload dos arquivos `.pdf` dos programas CNC.")
pdfs = st.file_uploader("Selecione os arquivos PDF", type="pdf", accept_multiple_files=True)

if st.button("📥 Processar PDFs"):
    for pdf in pdfs:
        caminho_pdf = PASTA_PDF / pdf.name
        with open(caminho_pdf, "wb") as f:
            f.write(pdf.read())

        # Extrai dados do PDF
        info = extrair_dados_por_posicao(caminho_pdf)

        if info:
            info["CNC"] = caminho_pdf.stem
            info["Caminho"] = str(caminho_pdf.resolve())

            espessura_raw = info["Espessura (mm)"]
            espessura_fmt = f"{int(round(espessura_raw * 100)):04d}"
            nome_txt = f"{info['Proposta']}-{espessura_fmt}-{info['Material']}-{info['CNC']}.txt"
            caminho_txt = PASTA_TXT_PRONTOS / nome_txt

            conteudo = "\n".join([f"{k}: {v}" for k, v in info.items()])
            with open(caminho_txt, "w", encoding="utf-8") as f:
                f.write(conteudo)

    st.success("Arquivos processados e salvos em 'Programas_Prontos/'")

# 2. Trabalhos pendentes de autorização
st.markdown("---")
st.subheader("🕓 Trabalhos aguardando autorização")
arquivos_pendentes = sorted(PASTA_TXT_PRONTOS.glob("*.txt"))

if not arquivos_pendentes:
    st.info("Nenhum trabalho pendente no momento.")
else:
    for txt in arquivos_pendentes:
        with open(txt, "r", encoding="utf-8") as f:
            conteudo = f.read()

        with st.expander(f"📄 {txt.name}"):
            st.text(conteudo)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Autorizar", key=f"auth_{txt.name}"):
                    shutil.move(txt, PASTA_AUTORIZADOS / txt.name)
                    st.success("Trabalho autorizado.")
                    st.rerun()
            with col2:
                if st.button("❌ Rejeitar", key=f"rej_{txt.name}"):
                    txt.unlink()
                    st.warning("Trabalho rejeitado e excluído.")
                    st.rerun()
