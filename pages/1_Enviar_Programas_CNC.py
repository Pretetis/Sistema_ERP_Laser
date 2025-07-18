import streamlit as st
import sys
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

from utils.supabase import upload_txt_to_supabase, deletar_arquivo_supabase, baixar_txt_conteudo
from utils.extracao import extrair_dados_por_posicao
from utils.Junta_Trabalhos import carregar_trabalhos
from utils.navegacao import barra_navegacao

# Adiciona caminho do projeto para importar corretamente
sys.path.append(str(Path(__file__).resolve().parent.parent))
st.set_page_config(page_title="Enviar Programas CNC", layout="wide")
st.title("📤 Enviar Programas CNC")
barra_navegacao()  # Exibe a barra no topo

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

# =====================
# 1. Upload dos PDFs
# =====================
st.markdown("Faça o upload dos arquivos `.pdf` dos programas CNC.")
pdfs = st.file_uploader("Selecione os arquivos PDF", type="pdf", accept_multiple_files=True)

if st.button("📥 Processar PDFs"):
    registros = []

    for pdf in pdfs:
        # Processa o PDF diretamente sem salvar localmente
        info = extrair_dados_por_posicao(pdf)

        if info:
            info["CNC"] = pdf.name
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
        # Envia diretamente para o Cloudinary
        nome_arquivo = f"{chave}.txt"  # chave é a string que você usa para agrupar, ok?
        upload_txt_to_supabase(nome_arquivo, conteudo, pasta="aguardando_aprovacao")

    st.success("Arquivos agrupados e enviados ao Supabase com sucesso!")

# =====================
# 2. Trabalhos pendentes agrupados
# =====================
st.markdown("---")
st.subheader("🕓 Trabalhos aguardando autorização")

trabalhos = carregar_trabalhos()
trabalhos = trabalhos["aguardando_aprovacao"]

if not trabalhos:
    st.info("Nenhum trabalho pendente no momento.")
else:
    for trabalho in trabalhos:
        with st.expander(f"🔹 {trabalho['Proposta']} | {trabalho['Espessura']} mm | {trabalho['Material']} | x {trabalho['Qtd Total']} | ⏱ {trabalho['Tempo Total']}"):

            data_processo = st.date_input("Data", key=f"data_{trabalho['Grupo']}", format="DD/MM/YYYY")
            processos_possiveis = ["Dobra", "Usinagem", "Solda", "Gravação", "Galvanização", "Pintura"]
            col_processos = st.columns(len(processos_possiveis))
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
                                    detalhe['Caminho'] = caminho or "Caminho desconhecido"

                                    linhas.append(f"Programador: {detalhe['Programador']}")
                                    linhas.append(f"CNC: {detalhe['CNC']}")
                                    linhas.append(f"Qtd Chapas: {detalhe['Qtd Chapas']}")
                                    linhas.append(f"Tempo Total: {detalhe['Tempo Total']}")
                                    linhas.append(f"Caminho: {detalhe['Caminho']}")
                                    linhas.append("")

                                # Envia para o Cloudinary
                                conteudo = "\n".join(linhas)
                                nome_arquivo = f"{trabalho['Grupo']}.txt"
                                upload_txt_to_supabase(nome_arquivo, conteudo, pasta="trabalhos_pendentes")

                    with col2:
                        # Exibindo a imagem do PDF sem salvar localmente
                        caminho_pdf = item.get("Caminho")
                        if caminho_pdf:
                            st.image(caminho_pdf, caption=f"CNC {item['CNC']}", use_container_width=True)
                        else:
                            st.warning("Pré-visualização indisponível.")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Autorizar", key=f"auth_{trabalho['Grupo']}"):
                    # Captura as escolhas do usuário
                    data_str = str(data_processo)
                    processos_str = ", ".join(processos_final) if processos_final else "Somente Corte"

                    # Prepara as informações complementares
                    nome_arquivo = f"{trabalho['Grupo']}.txt"

                    # Primeiro, recupera o conteúdo atual da pasta aguardando_aprovacao
                    conteudo_atual = baixar_txt_conteudo(nome_arquivo, bucket="aguardando_aprovacao")

                    # Complementa com as informações adicionais
                    conteudo_complementado = (
                        conteudo_atual + "\n"
                        + "===== INFORMAÇÕES ADICIONAIS =====\n"
                        + f"Data prevista: {data_str}\n"
                        + f"Processos: {processos_str}\n"
                    )

                    # Envia para a pasta TRABALHOS_PENDENTES
                    upload_txt_to_supabase(nome_arquivo, conteudo_complementado, pasta="trabalhos_pendentes")

                    # Agora sim remove da aguardando_aprovacao
                    deletar_arquivo_supabase(nome_arquivo, bucket="aguardando_aprovacao")

                    st.success(f"Trabalho do grupo {trabalho['Grupo']} autorizado.")
                    st.rerun()

            with col2:
                if st.button("❌ Rejeitar", key=f"rej_{trabalho['Grupo']}"):
                    # Remove do Cloudinary da pasta aguardando_aprovacao
                    deletar_arquivo_supabase(f"{trabalho['Grupo']}.txt", bucket="aguardando_aprovacao")
                    st.warning(f"Trabalho do grupo {trabalho['Grupo']} rejeitado.")
                    st.rerun()