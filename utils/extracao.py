import fitz  # PyMuPDF
from pathlib import Path
from utils.visualizacao import gerar_preview_pdf
from utils.cloudinary_txt import enviar_txt_cloudinary

def extrair_dados_por_posicao(caminho_pdf):
    doc = fitz.open(caminho_pdf)
    pagina = doc[0]
    blocos = pagina.get_text("blocks")

    link_cloudinary = gerar_preview_pdf(caminho_pdf)

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
            "Caminho": link_cloudinary
        }
    else:
        return None

# 🗂️ Pastas
pasta_cnc = Path("CNC")
pasta_saida = Path("Programas_Prontos")
pasta_saida.mkdir(exist_ok=True)

# 🔍 Processa PDFs da pasta CNC
arquivos_pdf = list(pasta_cnc.glob("*.pdf"))

for arquivo in arquivos_pdf:
    info = extrair_dados_por_posicao(arquivo)
    if info:
        info["CNC"] = arquivo.stem

        # Cria nome do arquivo com base nas colunas
        espessura_raw = info["Espessura (mm)"]
        espessura_formatada = f"{int(round(espessura_raw * 100)):04d}"
        nome_arquivo = f"{info['Proposta']}-{espessura_formatada}-{info['Material']}-{info['CNC']}.txt"
        caminho_arquivo = pasta_saida / nome_arquivo

        # Conteúdo do arquivo
        conteudo = "\n".join([f"{chave}: {valor}" for chave, valor in info.items()])

        # Salva o arquivo
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo)

        # Lê o conteúdo do arquivo para string
        conteudo = caminho_arquivo.read_text(encoding="utf-8")

        # Extrai apenas o nome do arquivo para o Cloudinary
        nome_arquivo = caminho_arquivo.name  # Ex: "PROP-0010-INOX-P001.txt"

        # Envia corretamente para o Cloudinary
        enviar_txt_cloudinary(conteudo, nome_arquivo=nome_arquivo, pasta="aguardando_aprovacao")

print("✅ Arquivos individuais salvos em 'Programas_Prontos/'.")
