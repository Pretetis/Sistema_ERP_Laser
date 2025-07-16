import streamlit as st
from pathlib import Path
import sys
import shutil
import pandas as pd
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=7000, key="data_refresh")


# Adiciona caminho do projeto para importar corretamente
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.extracao import extrair_dados_por_posicao
from utils.Junta_Trabalhos import carregar_trabalhos
from utils.navegacao import barra_navegacao
from utils.visualizacao import gerar_preview_pdf

st.set_page_config(page_title="Minha Página", layout="wide")

st.markdown(
        """
        <style>
        .stExpander p {
            font-size: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

barra_navegacao()  # Exibe a barra no topo


# Caminhos das pastas
RAIZ = Path(__file__).resolve().parent.parent
PASTA_PDF = RAIZ / "CNC"
PASTA_TXT_PRONTOS = RAIZ / "Programas_Prontos"
PASTA_AUTORIZADOS = RAIZ / "autorizados"

# Garante que as pastas existem
PASTA_PDF.mkdir(exist_ok=True)
PASTA_TXT_PRONTOS.mkdir(exist_ok=True)
PASTA_AUTORIZADOS.mkdir(exist_ok=True)

st.set_page_config(page_title="Enviar Programas CNC", layout="wide")
st.title("📤 Enviar Programas CNC")

# =====================
# 1. Upload dos PDFs
# =====================
st.markdown("Faça o upload dos arquivos `.pdf` dos programas CNC.")
pdfs = st.file_uploader("Selecione os arquivos PDF", type="pdf", accept_multiple_files=True)

if st.button("📥 Processar PDFs"):
    registros = []

    for pdf in pdfs:
        caminho_pdf = PASTA_PDF / pdf.name
        with open(caminho_pdf, "wb") as f:
            f.write(pdf.read())

        info = extrair_dados_por_posicao(caminho_pdf)

        if info:
            info["CNC"] = caminho_pdf.stem
            info["Caminho"] = str(caminho_pdf.resolve())
            registros.append(info)

    # Agrupamento por chave: Proposta-Espessura-Material
    from collections import defaultdict
    grupos = defaultdict(list)

    for r in registros:
        espessura_fmt = f"{int(round(r['Espessura (mm)'] * 100)):04d}"
        chave = f"{r['Proposta']}-{espessura_fmt}-{r['Material']}"
        grupos[chave].append(r)

    for chave, lista in grupos.items():
        linhas = []
        for item in lista:
            linhas.append(f"Programador: {item['Programador']}")
            linhas.append(f"CNC: {item['CNC']}")
            linhas.append(f"Qtd Chapas: {item['Qtd Chapas']}")
            linhas.append(f"Tempo Total: {item['Tempo Total']}")
            linhas.append(f"Caminho: {item['Caminho']}")
            linhas.append("")

        conteudo = "\n".join(linhas)
        caminho_txt = PASTA_TXT_PRONTOS / f"{chave}.txt"  # ✅ sem CNC no nome
        with open(caminho_txt, "w", encoding="utf-8") as f:
            f.write(conteudo)

    st.success("Arquivos agrupados salvos em 'Programas_Prontos'")

# =====================
# 2. Trabalhos pendentes agrupados
# =====================
st.markdown("---")
st.subheader("🕓 Trabalhos aguardando autorização")

trabalhos = carregar_trabalhos(pasta="Programas_Prontos")

if not trabalhos:
    st.info("Nenhum trabalho pendente no momento.")
else:
    for trabalho in trabalhos:
        with st.expander(f"🔹 {trabalho['Proposta']} | {trabalho['Espessura']} mm | {trabalho['Material']} | x {trabalho['Qtd Total']} | ⏱ {trabalho['Tempo Total']}"):
            # 👉 Novo campo de data
            data_processo = st.date_input("Data", key=f"data_{trabalho['Grupo']}", format="DD/MM/YYYY")

            # 👉 Campo de seleção múltipla de processos com opção "Somente Corte"
            processos_possiveis = ["Dobra", "Usinagem", "Solda", "Gravação", "Galvanização", "Pintura"]

            # Criar checkboxes na mesma linha
            col_processos = st.columns(len(processos_possiveis))

            # Guardar os processos marcados
            processos_selecionados = []

            for i, processo in enumerate(processos_possiveis):
                if col_processos[i].checkbox(processo, key=f"proc_{trabalho['Grupo']}_{processo}"):
                    processos_selecionados.append(processo)

            # Se nenhum foi selecionado, considerar "Somente Corte"
            if not processos_selecionados:
                processos_final = []
            else:
                processos_final = processos_selecionados

            for item in trabalho["Detalhes"]:
                with st.container(border=True):
                    col1, col2 = st.columns([2, 2])

                    with col1:
                        st.markdown(f"**Programador:** {item['Programador']}")
                        st.markdown(f"**CNC:** {item['CNC']}")
                        st.markdown(f"**Qtd Chapas:** {item['Qtd Chapas']}")

                        # Aqui começa o código para editar o tempo
                        tempo_key = f"tempo_edit_{item['CNC']}"  # chave única
                        editar_key = f"editar_tempo_{item['CNC']}"

                        st.markdown(f"**Tempo Total:** {item['Tempo Total']}")

                        if st.button("Editar Tempo", key=editar_key):
                            st.session_state[tempo_key] = True

                        if st.session_state.get(tempo_key, False):
                            col_h, col_m, col_s = st.columns(3)

                            horas = col_h.number_input("Horas", min_value=0, value=0, key=f"h_{item['CNC']}")
                            minutos = col_m.number_input("Min", min_value=0, max_value=59, value=0, key=f"m_{item['CNC']}")
                            segundos = col_s.number_input("Seg", min_value=0, max_value=59, value=0, key=f"s_{item['CNC']}")
                            tempo_editado = f"{int(horas):02d}:{int(minutos):02d}:{int(segundos):02d}"

                            if st.button("Salvar", key=f"salvar_{item['CNC']}"):
                                item['Tempo Total'] = tempo_editado
                                st.session_state[tempo_key] = False

                                linhas = []
                                for detalhe in trabalho["Detalhes"]:
                                    # Garantir que "Caminho" não esteja vazio
                                    caminho = detalhe.get('Caminho')
                                    if not caminho and 'CNC' in detalhe:
                                        possivel = PASTA_PDF / f"{detalhe['CNC']}.pdf"
                                        caminho = str(possivel.resolve()) if possivel.exists() else ""

                                    detalhe['Caminho'] = caminho or "Caminho desconhecido"

                                    linhas.append(f"Programador: {detalhe['Programador']}")
                                    linhas.append(f"CNC: {detalhe['CNC']}")
                                    linhas.append(f"Qtd Chapas: {detalhe['Qtd Chapas']}")
                                    linhas.append(f"Tempo Total: {detalhe['Tempo Total']}")
                                    linhas.append(f"Caminho: {detalhe['Caminho']}")
                                    linhas.append("")

                                caminho_txt = PASTA_TXT_PRONTOS / f"{trabalho['Grupo']}.txt"
                                with open(caminho_txt, "w", encoding="utf-8") as f:
                                    f.write("\n".join(linhas))

                    with col2:
                        caminho_pdf = item.get("Caminho PDF") or item.get("Caminho")
                        if caminho_pdf and Path(caminho_pdf).exists():
                            preview_path = gerar_preview_pdf(caminho_pdf)
                            if preview_path:
                                st.image(preview_path, caption=f"CNC {item['CNC']}", use_container_width="auto")
                            else:
                                st.warning("Erro ao gerar preview.")
                        else:
                            st.warning("Arquivo PDF não encontrado.")


            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Autorizar", key=f"auth_{trabalho['Grupo']}"):
                    # Captura as escolhas do usuário
                    data_str = str(data_processo)
                    processos_str = ", ".join(processos_final) if processos_final else "Somente Corte"

                    origem = f"{trabalho['Grupo']}.txt"
                    origem_path = PASTA_TXT_PRONTOS / origem
                    destino_path = PASTA_AUTORIZADOS / origem

                    if origem_path.exists():
                        # Lê o conteúdo original
                        with open(origem_path, "r", encoding="utf-8") as f:
                            conteudo_original = f.read()

                        # Adiciona os dados extras ao final
                        conteudo_complementado = (
                            conteudo_original.strip()
                            + "\n\n"
                            + "===== INFORMAÇÕES ADICIONAIS =====\n"
                            + f"Data prevista: {data_str}\n"
                            + f"Processos: {processos_str}\n"
                        )

                        # Salva no destino com o conteúdo completo
                        with open(destino_path, "w", encoding="utf-8") as f:
                            f.write(conteudo_complementado)

                        origem_path.unlink()  # Remove o original da pasta de pendentes

                        st.success(f"Trabalho do grupo {trabalho['Grupo']} autorizado.")
                        st.rerun()
            with col2:
                if st.button("❌ Rejeitar", key=f"rej_{trabalho['Grupo']}"):
                    for item in trabalho["Detalhes"]:
                        txt_path = PASTA_TXT_PRONTOS /  f"{trabalho['Grupo']}.txt"
                        if txt_path.exists():
                            txt_path.unlink()
                    st.warning(f"Trabalho do grupo {trabalho['Grupo']} rejeitado.")
                    st.rerun()