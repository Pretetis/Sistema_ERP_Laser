import fitz  # PyMuPDF
import tempfile
from pathlib import Path

from utils.supabase import upload_imagem_to_supabase
from utils.db import inserir_trabalho_pendente

# 🗂️ Pasta onde estão os PDFs
pasta_cnc = Path("CNC")

def gerar_preview_pdf(pdf_path: Path, nome_saida: str) -> Path:
    with pdf_path.open("rb") as f:
        doc = fitz.open(stream=f.read(), filetype="pdf")
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)

    temp_img_path = Path(tempfile.gettempdir()) / f"{nome_saida}.png"
    pix.save(temp_img_path)
    return temp_img_path


def extrair_dados_por_posicao(arquivo_pdf):
    arquivo_pdf.seek(0)
    doc = fitz.open(stream=arquivo_pdf, filetype="pdf")
    pagina = doc[0]
    blocos = pagina.get_text("blocks")

    # Salva temporariamente para gerar preview
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(arquivo_pdf.read())
        caminho_temp = Path(tmp_file.name)

    nome_saida = caminho_temp.stem
    preview_path = gerar_preview_pdf(caminho_temp, nome_saida)
    link_supabase = upload_imagem_to_supabase(preview_path, destino="previews")

    arquivo_pdf.seek(0)

    proposta = espessura = material = programador = tempo_total = None
    qtd_chapas = 0

    for x0, y0, x1, y1, texto, *_ in blocos:
        if 397 <= x0 <= 456 and 463 <= y0 <= 470:
            partes = texto.strip().split("-")
            if len(partes) == 3:
                proposta = partes[0]
                espessura = int(partes[1]) / 100
                material = partes[2]

        if 463 <= x0 <= 555 and 463 <= y0 <= 470:
            linhas = texto.strip().split("\n")
            if len(linhas) == 3:
                try:
                    qtd_chapas = int(linhas[0])
                    tempo_total = linhas[1]
                    programador = linhas[2]
                except:
                    pass

    if all([proposta, espessura, material, programador, tempo_total]):
        return {
            "proposta": proposta,
            "espessura": espessura,
            "material": material,
            "programador": programador,
            "qtd_chapas": qtd_chapas,
            "tempo_total": tempo_total,
            "caminho": link_supabase
        }
    else:
        return None


# 🔍 Processa todos os PDFs na pasta CNC e salva no banco
def processar_pdfs_da_pasta():
    arquivos_pdf = list(pasta_cnc.glob("*.pdf"))

    for arquivo in arquivos_pdf:
        with arquivo.open("rb") as f:
            info = extrair_dados_por_posicao(f)

        if info:
            cnc = arquivo.stem
            espessura_fmt = f"{int(round(info['espessura'] * 100)):04d}"
            grupo = f"{info['proposta']}-{espessura_fmt}-{info['material']}"

            inserir_trabalho_pendente({
                "grupo": grupo,
                "proposta": info["proposta"],
                "espessura": info["espessura"],
                "material": info["material"],
                "cnc": cnc,
                "programador": info["programador"],
                "qtd_chapas": info["qtd_chapas"],
                "tempo_total": info["tempo_total"],
                "caminho": info["caminho"],
                "data_prevista": None,
                "processos": [],
                "autorizado": False,
                "gas": []
            })

    print("✅ PDFs processados e inseridos no banco de dados.")
