import fitz  # PyMuPDF
import tempfile
from pathlib import Path

from utils.supabase import upload_txt_to_supabase, upload_imagem_to_supabase

# 🗂️ Pastas
pasta_cnc = Path("CNC")
pasta_saida = Path("Programas_Prontos")
pasta_saida.mkdir(exist_ok=True)


def gerar_preview_pdf(pdf_path: Path, nome_saida: str) -> Path:
    with pdf_path.open("rb") as f:
        doc = fitz.open(stream=f.read(), filetype="pdf")
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)

    # Salva temporariamente como imagem
    temp_img_path = Path(tempfile.gettempdir()) / f"{nome_saida}.png"
    pix.save(temp_img_path)
    return temp_img_path

def extrair_dados_por_posicao(arquivo_pdf):
    arquivo_pdf.seek(0)
    doc = fitz.open(stream=arquivo_pdf, filetype="pdf")
    pagina = doc[0]
    blocos = pagina.get_text("blocks")

    # Salva temporariamente para gerar o preview
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(arquivo_pdf.read())
        caminho_temp = Path(tmp_file.name)

    # Gera preview e envia para o Supabase
    nome_saida = caminho_temp.stem
    preview_path = gerar_preview_pdf(caminho_temp, nome_saida)
    link_supabase = upload_imagem_to_supabase(preview_path, destino="previews")

    arquivo_pdf.seek(0)  # Reposiciona ponteiro se quiser reutilizar

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
            "Proposta": proposta,
            "Espessura (mm)": espessura,
            "Material": material,
            "Programador": programador,
            "Qtd Chapas": qtd_chapas,
            "Tempo Total": tempo_total,
            "Caminho": link_supabase
        }
    else:
        return None

# 🔍 Processa PDFs da pasta CNC
arquivos_pdf = list(pasta_cnc.glob("*.pdf"))

for arquivo in arquivos_pdf:
    with arquivo.open("rb") as f:
        info = extrair_dados_por_posicao(f)
    if info:
        info["CNC"] = arquivo.stem

        espessura_raw = info["Espessura (mm)"]
        espessura_formatada = f"{int(round(espessura_raw * 100)):04d}"
        nome_arquivo = f"aguardando_aprovacao-{info['Proposta']}-{espessura_formatada}-{info['Material']}-{info['CNC']}.txt"
        caminho_arquivo = pasta_saida / nome_arquivo

        conteudo = "\n".join([f"{chave}: {valor}" for chave, valor in info.items()])
        caminho_arquivo.write_text(conteudo, encoding="utf-8")

        # Releitura (opcional)
        conteudo = caminho_arquivo.read_text(encoding="utf-8")

        # Upload para Supabase
        upload_txt_to_supabase(nome_arquivo, conteudo)

print("✅ Arquivos individuais salvos em 'Programas_Prontos/' e enviados ao Supabase.")
