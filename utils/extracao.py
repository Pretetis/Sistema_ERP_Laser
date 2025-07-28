import fitz  # PyMuPDF
from io import BytesIO
from PIL import Image
from pathlib import Path
from datetime import datetime

from utils.supabase import supabase, BUCKET_NAME, SUPABASE_URL


def gerar_preview_pdf_em_memoria(pdf_bytes: bytes) -> Image.Image:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def upload_imagem_memoria_to_supabase(imagem_pil: Image.Image, nome: str, destino: str = "previews") -> str:
    buffer = BytesIO()
    imagem_pil.save(buffer, format="PNG")
    buffer.seek(0)

    destino_final = f"{destino}/{nome}.png"
    file_bytes = buffer.read()

    storage = supabase.storage.from_(BUCKET_NAME)

    # Verificar se o arquivo já existe no bucket
    try:
        storage.download(destino_final)
        existe = True
    except Exception:
        existe = False

    # Se existir, atualiza. Se não, faz upload.
    if existe:
        storage.update(
            path=destino_final,
            file=file_bytes,
            file_options={"content-type": "image/png"}
        )
    else:
        storage.upload(
            path=destino_final,
            file=file_bytes,
            file_options={"content-type": "image/png"}
        )

    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{destino_final}"



def extrair_dados_por_posicao(arquivo_pdf):
    arquivo_pdf.seek(0)
    pdf_bytes = arquivo_pdf.read()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pagina = doc[0]
    blocos = pagina.get_text("blocks")

    nome_arquivo = f"preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  # valor padrão

    if hasattr(arquivo_pdf, "name"):
        try:
            nome_arquivo_temp = Path(arquivo_pdf.name).stem
            if nome_arquivo_temp:  # Garante que não é vazio
                nome_arquivo = nome_arquivo_temp
        except Exception as e:
            print(f"Erro ao extrair nome do arquivo: {e}")

    # Gerar preview em memória
    imagem_preview = gerar_preview_pdf_em_memoria(pdf_bytes)
    link_supabase = upload_imagem_memoria_to_supabase(imagem_preview, nome=nome_arquivo, destino="previews")

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
