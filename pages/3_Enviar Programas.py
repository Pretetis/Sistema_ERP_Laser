import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import date

from utils.auth import verificar_autenticacao
verificar_autenticacao(roles_permitidos=["Programador", "Gerente"])

from utils.extracao import extrair_dados_por_posicao
from utils.Junta_Trabalhos import carregar_trabalhos
from utils.db import inserir_trabalho_pendente, atualizar_trabalho_pendente, excluir_trabalhos_grupo
from utils.supabase import excluir_imagem_supabase


# Adiciona caminho do projeto para importar corretamente
sys.path.append(str(Path(__file__).resolve().parent.parent))
st.set_page_config(page_title="Enviar Programas CNC", layout="wide")
st.title("📤 Enviar Programas CNC")

st.markdown("""
    <style>
    .stExpander p {
        font-size: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# =====================
# 1. Upload dos PDFs
# =====================
st.markdown("Faça o upload dos arquivos .pdf dos programas CNC.")
pdfs = st.file_uploader("Selecione os arquivos PDF", type="pdf", accept_multiple_files=True)

from pathlib import Path
import pandas as pd  # se ainda não importou

if st.button("🗕️ Processar PDFs"):
    for pdf in pdfs:
        info = extrair_dados_por_posicao(pdf)
        if info:
            cnc = Path(pdf.name).stem  # Remove .pdf
            
            # Se tempo_total é string, converte para timedelta
            tempo_td = pd.to_timedelta(info["tempo_total"]) if isinstance(info["tempo_total"], str) else info["tempo_total"]
            
            total_segundos = int(tempo_td.total_seconds())
            tempo_formatado = f"{total_segundos // 3600:02}:{(total_segundos % 3600) // 60:02}:{total_segundos % 60:02}"
            
            inserir_trabalho_pendente({
                "grupo": f"{info['proposta']}-{int(round(info['espessura']*100)):04d}-{info['material']}",
                "proposta": info["proposta"],
                "espessura": info["espessura"],
                "material": info["material"],
                "cnc": cnc,
                "programador": info["programador"],
                "qtd_chapas": info["qtd_chapas"],
                "tempo_total": tempo_formatado,  # tempo formatado no padrão HH:MM:SS
                "caminho": info["caminho"],
                "data_prevista": date.today().isoformat(),
                "processos": [],
                "autorizado": False,
                "gas": []
            })
    st.success("PDFs processados e registrados no banco de dados!")

# =====================
# 2. Trabalhos pendentes agrupados
# =====================
st.markdown("---")
st.subheader("🕓 Trabalhos aguardando autorização")

trabalhos = carregar_trabalhos()["aguardando_aprovacao"]

# Inicializa o estado das edições
for trabalho in trabalhos:
    for item in trabalho["detalhes"]:
        tempo_key = f"tempo_edit_{trabalho['grupo']}_{item['cnc']}"
        if tempo_key not in st.session_state:
            st.session_state[tempo_key] = False

if not trabalhos:
    st.info("Nenhum trabalho pendente no momento.")
else:
    for trabalho in trabalhos:
        with st.expander(
            f"🔹 {trabalho['proposta']} | {trabalho['espessura']} mm | {trabalho['material']} "
            f"| x {trabalho['qtd_total']} | ⏱ {trabalho['tempo_total']}"
        ):
            data_processo = st.date_input("Data", key=f"data_{trabalho['grupo']}", format="DD/MM/YYYY")

            processos_possiveis = ["Dobra", "Usinagem", "Solda", "Gravação", "Galvanização", "Pintura"]
            gas_escolhido = st.radio(
                "Selecione o gás",
                options=["Padrão", "Nitrogênio", "Oxigênio", "Ar Comprimido", "Vaporizado"],
                index=0,
                key=f"gas_{trabalho['grupo']}",
                horizontal=True
            )

            gas_final = None if gas_escolhido == "Padrão" else gas_escolhido

            col_processos = st.columns(len(processos_possiveis))
            processos_selecionados = [
                proc for i, proc in enumerate(processos_possiveis)
                if col_processos[i].checkbox(proc, key=f"proc_{trabalho['grupo']}_{proc}")
            ]

            for item in trabalho["detalhes"]:
                with st.container(border=True):
                    col1, col2 = st.columns([2, 2])

                    with col1:
                        st.markdown(f"**Programador:** {item.get('programador', 'DESCONHECIDO')}")
                        st.markdown(f"**CNC:** {item.get('cnc', 'DESCONHECIDO').replace('.pdf', '')}")
                        st.markdown(f"**Qtd Chapas:** {item.get('qtd_chapas', 'DESCONHECIDO')}")
                        st.markdown(f"**Tempo Total:** {item.get('tempo_total', 'DESCONHECIDO')}")

                        tempo_key = f"tempo_edit_{trabalho['grupo']}_{item['cnc']}"
                        editar_key = f"editar_tempo_{trabalho['grupo']}_{item['cnc']}"

                        if st.button("Editar Tempo", key=editar_key):
                            st.session_state[tempo_key] = True

                        if st.session_state.get(tempo_key, False):
                            col_h, col_m, col_s = st.columns(3)
                            horas = col_h.number_input("Horas", min_value=0, value=0, key=f"h_{trabalho['grupo']}_{item['cnc']}")
                            minutos = col_m.number_input("Min", min_value=0, max_value=59, value=0, key=f"m_{trabalho['grupo']}_{item['cnc']}")
                            segundos = col_s.number_input("Seg", min_value=0, max_value=59, value=0, key=f"s_{trabalho['grupo']}_{item['cnc']}")
                            tempo_editado = f"{int(horas):02d}:{int(minutos):02d}:{int(segundos):02d}"

                            if st.button("Salvar Tempo", key=f"salvar_{item['cnc']}"):
                                atualizar_trabalho_pendente(
                                    cnc=item['cnc'],
                                    grupo=trabalho['grupo'],
                                    tempo_total=tempo_editado,
                                    gas=gas_final
                                )
                                st.success("Tempo atualizado com sucesso!")
                                st.session_state[tempo_key] = False
                                st.rerun()

                    with col2:
                        caminho_pdf = item.get("caminho")
                        if caminho_pdf:
                            st.image(caminho_pdf, caption=f"CNC {item['cnc']}", use_container_width=True)
                        else:
                            st.warning("Pré-visualização indisponível.")

            # Botões de autorizar/rejeitar agora dentro de uma form controlada
            with st.form(key=f"form_aut_{trabalho['grupo']}"):
                col1, col2 = st.columns(2)

                with col1:
                    autorizar = st.form_submit_button("✅ Autorizar")
                with col2:
                    rejeitar = st.form_submit_button("❌ Rejeitar")

                if autorizar:
                    data_str = str(data_processo)
                    processos_final = processos_selecionados or []

                    for item in trabalho["detalhes"]:
                        atualizar_trabalho_pendente(
                            cnc=item['cnc'],
                            grupo=trabalho['grupo'],
                            tempo_total=item['tempo_total'],
                            data_prevista=data_str,
                            processos=processos_final,
                            autorizado=True,
                            gas=gas_final
                        )

                    st.success(f"Trabalho do grupo {trabalho['grupo']} autorizado.")
                    st.rerun()

                if rejeitar:
                    caminho_imagem = trabalho.get("caminho")
                    if caminho_imagem:
                        sucesso = excluir_imagem_supabase(caminho_imagem)
                        if sucesso:
                            st.info("Imagem excluída com sucesso.")
                        else:
                            st.warning("Falha ao excluir a imagem.")

                    excluir_trabalhos_grupo(trabalho["grupo"])
                    st.warning(f"Trabalho do grupo {trabalho['grupo']} rejeitado.")
                    st.rerun()
