import streamlit as st
import pandas as pd
from streamlit_sortables import sort_items
from utils.supabase import supabase

from utils.Junta_Trabalhos import carregar_trabalhos
from utils.db import (
    adicionar_na_fila, obter_fila, atualizar_trabalho_pendente,
    obter_corte_atual, iniciar_corte, finalizar_corte,
    retornar_para_pendentes, retomar_interrupcao,
    retornar_item_da_fila_para_pendentes, excluir_trabalhos_grupo,
    registrar_evento, mostrar_grafico_eventos
)

MAQUINAS = ["LASER 1", "LASER 2", "LASER 3", "LASER 4", "LASER 5", "LASER 6"]

from streamlit_autorefresh import st_autorefresh
from utils.navegacao import barra_navegacao

# Atualiza automaticamente a cada 7 segundos
#st_autorefresh(interval=7000, key="data_refresh")

st.set_page_config(page_title="Gestão de Corte", layout="wide")
barra_navegacao()
st.title("🛠️ Gestão de Produção")

# =====================
# Sidebar - Trabalhos Agrupados
# =====================
st.sidebar.title("📋 Trabalhos Pendentes")
trabalhos = carregar_trabalhos()
trabalhos_pendentes = trabalhos.get("trabalhos_pendentes", [])

for trabalho in trabalhos_pendentes:
    titulo = (
        f"🔹 {trabalho.get('proposta', 'N/D')} | {trabalho.get('espessura', 'N/D')} mm | "
        f"{trabalho.get('material', 'N/D')} | x {trabalho.get('qtd_total', 'N/D')} | "
        f"⏱ {trabalho.get('tempo_total', 'N/D')}"
    )

    if trabalho.get("data_prevista"):
        try:
            data_fmt = "/".join(reversed(trabalho["data_prevista"].split("-")))
            titulo += f" | 📅 {data_fmt}"
        except Exception:
            pass

    if trabalho.get("processos"):
        titulo += f" | ⚙️ {trabalho.get('processos')}"

    with st.sidebar.expander(titulo):
        # Seleção da máquina depois dos botões
        maquina_escolhida = st.selectbox("Enviar para:", MAQUINAS, key=f"sel_maquina_{trabalho.get('grupo', '')}")
        col_add, col_del = st.columns(2)
        with col_add:
            if st.button("➕ Adicionar à máquina", key=f"btn_{trabalho.get('grupo', '')}"):
                for item in trabalho.get("detalhes", []):
                    adicionar_na_fila(maquina_escolhida, {
                        "proposta": trabalho.get("proposta", ""),
                        "cnc": item.get("cnc", ""),
                        "material": trabalho.get("material", ""),
                        "espessura": trabalho.get("espessura", 0),
                        "qtd_chapas": int(item.get("qtd_chapas", 0)),
                        "tempo_total": item.get("tempo_total", ""),
                        "caminho": item.get("caminho", ""),
                        "programador": item.get("programador", "DESCONHECIDO")
                    })

                    atualizar_trabalho_pendente(
                        cnc=item.get("cnc", ""),
                        grupo=trabalho.get("grupo", ""),
                        tempo_total=item.get("tempo_total", ""),
                        data_prevista=trabalho.get("data_prevista"),
                        processos=trabalho.get("processos"),
                        autorizado=True
                    )

                excluir_trabalhos_grupo(trabalho.get("grupo", ""))
                st.success(f"Trabalho enviado para {maquina_escolhida}")
                st.rerun()

        with col_del:
            if st.button("🖑 Excluir Trabalho", key=f"del_{trabalho.get('grupo', '')}"):
                excluir_trabalhos_grupo(trabalho.get("grupo", ""))
                st.success("Trabalho excluído.")
                st.rerun()

        # Detalhes abaixo, como já faz:
        for item in trabalho.get("detalhes", []):
            with st.container(border=True):
                col1, col2 = st.columns([2, 2])
                with col1:
                    st.markdown(f"**Programador:** {item.get('programador', 'DESCONHECIDO')}")
                    st.markdown(f"**CNC:** {item.get('cnc', 'DESCONHECIDO')}")
                    st.markdown(f"**Qtd Chapas:** {item.get('qtd_chapas', 'DESCONHECIDO')}")
                    st.markdown(f"**Tempo Total:** {item.get('tempo_total', 'DESCONHECIDO')}")

                with col2:
                    caminho_imagem = item.get("caminho")
                    if caminho_imagem and caminho_imagem.startswith("http") and caminho_imagem.lower().endswith((".png", ".jpg", ".jpeg")):
                        st.image(caminho_imagem, caption=f"CNC {item.get('cnc', '')}", use_container_width=True)
                    else:
                        st.warning("Imagem de pré-visualização não encontrada.")

# =====================
# Painel Principal - Máquinas
# =====================
st.markdown("---")
cols = st.columns(1)

@st.dialog("Interrupção de Corte")
def abrir_dialogo_interrupcao(maquina):
    motivo = st.text_area("Motivo da Interrupção", key=f"motivo_{maquina}")
    if st.button("Confirmar Parada", key=f"confirmar_parada_{maquina}"):
        corte = obter_corte_atual(maquina)
        if corte:
            registrar_evento(maquina, "parado", corte["proposta"], corte["cnc"], motivo=motivo)
            st.success("Interrupção registrada.")
            st.rerun()

def trocar_posicao(id1, pos1, id2, pos2):
    # Troca as posições de dois itens na fila
    supabase.table("fila_maquinas").update({"posicao": pos2}).eq("id", id1).execute()
    supabase.table("fila_maquinas").update({"posicao": pos1}).eq("id", id2).execute()

for i, maquina in enumerate(MAQUINAS):
    with st.container(border=True):
        st.markdown(f"## 🔧 {maquina}")

        corte = obter_corte_atual(maquina)
        fila = obter_fila(maquina)  # já vem ordenada por 'posicao'

        if corte:
            st.markdown(
                f"**🔹 Corte Atual:** {corte.get('qtd_chapas', 'N/D')} | CNC {corte.get('cnc', 'N/D')} | "
                f"{corte.get('material', 'N/D')} | {corte.get('espessura', 'N/D')} mm"
            )
            col_fim, col_intr, col_ret, col_pend = st.columns(4)

            with col_fim:
                if st.button("✅ Finalizar Corte Atual", key=f"fim_{maquina}"):
                    finalizar_corte(maquina)
                    st.success("Corte finalizado")
                    st.rerun()

            with col_intr:
                if st.button("⏸️ Parar Corte", key=f"parar_{maquina}"):
                    abrir_dialogo_interrupcao(maquina)

            with col_ret:
                if st.button("▶️ Retomar Corte", key=f"retomar_{maquina}"):
                    retomar_interrupcao(maquina)
                    st.success("Corte retomado.")
                    st.rerun()

            with col_pend:
                if st.button("🔁 Retornar para Pendentes", key=f"ret_{maquina}"):
                    retornar_para_pendentes(maquina)
                    st.success("Trabalho retornado para pendentes")
                    st.rerun()
        else:
            st.markdown("_Nenhum corte em andamento_")

        st.divider()

        if fila:
            aba_visual, aba_ordenacao = st.tabs(["📄 Visualização Completa", "🔃 Ordem de Corte"])

            with aba_visual:
                st.markdown("### 📋 Fila de Espera")

                dados_fila = []
                for item in fila:
                    dados_fila.append({
                        "ID": item.get("id"),
                        "Máquina": item.get("maquina"),
                        "Proposta": item.get("proposta"),
                        "CNC": item.get("cnc"),
                        "Material": item.get("material"),
                        "Espessura": item.get("espessura"),
                        "Quantidade": item.get("qtd_chapas"),
                        "Tempo": item.get("tempo_total"),
                        "Caminho": item.get("caminho", ""),
                        "Local Separado": item.get("local_separado", "")
                    })

                df_visual = pd.DataFrame(dados_fila)

                config = {
                    "Caminho": st.column_config.ImageColumn(),
                    "Local Separado": st.column_config.TextColumn(disabled=False)
                }

                for col in df_visual.columns:
                    if col not in ["Local Separado", "Caminho"]:
                        config[col] = st.column_config.TextColumn(disabled=True)

                edited_df = st.data_editor(
                    df_visual.drop(columns=["ID"]),  # ID só usado internamente
                    column_config=config,
                    hide_index=True,
                    use_container_width=True,
                    key=f"data_editor_{maquina}"
                )

                if st.button(f"💾 Salvar 'Local Separado' - {maquina}"):
                    for idx, novo_valor in enumerate(edited_df["Local Separado"]):
                        id_item = dados_fila[idx]["ID"]
                        supabase.table("fila_maquinas").update({"local_separado": novo_valor}).eq("id", id_item).execute()
                    st.success("Campos salvos com sucesso.")
                    st.rerun()

                opcoes = {
                    f"{item['proposta']} | CNC {item['cnc']}": item['id']
                    for item in fila
                }

                escolha = st.selectbox("Escolha o próximo CNC:", list(opcoes.keys()), key=f"escolha_{maquina}")
                col_iniciar, col_ret = st.columns(2)

                with col_iniciar:
                    if st.button("▶️ Iniciar Corte", key=f"iniciar_{maquina}"):
                        if corte:
                            st.warning("Finalize o corte atual antes de iniciar um novo.")
                        else:
                            iniciar_corte(maquina, opcoes[escolha])
                            st.success("Corte iniciado.")
                            st.rerun()

                with col_ret:
                    if st.button("🔁 Retornar CNC para Pendentes", key=f"ret_fila_{maquina}"):
                        retornar_item_da_fila_para_pendentes(opcoes[escolha])
                        st.success("Item da fila retornado para pendentes.")
                        st.rerun()
            with aba_ordenacao:
                st.markdown("### 🔃 Ordem de Corte")

                mapa_itens = {}
                elementos_drag = []

                for item in fila:
                    # Garante unicidade no rótulo com ID oculto
                    label = f"""📌 Proposta: {item['proposta']} | 📄 CNC: {item['cnc']} | 🧪 Material: {item['material']} | Esp: {item['espessura']} mm  
            📦 Qtd: {item['qtd_chapas']} | ⏱️ Tempo: {item.get('tempo_total', '')} | ID: {item['id']}"""  # ID invisível para diferenciar

                    elementos_drag.append(label)
                    mapa_itens[label] = item["id"]

                estilo_azul_escuro = """
                .sortable-component {
                    background-color: #0F1117;
                    font-family: monospace;
                    font-size: 16px;
                    counter-reset: item;
                }
                .sortable-container {
                    background-color: #14161A;
                    border: 2px solid #00CFFF;
                    border-radius: 10px;
                    padding: 5px;
                }
                .sortable-container-header {
                    background-color: #0E1117;
                    color: #00FFFF;
                    font-weight: bold;
                    padding: 0.5rem 1rem;
                }
                .sortable-container-body {
                    background-color: #14161A;
                }
                .sortable-item, .sortable-item:hover {
                    background-color: #0E1117;
                    color: #FFFFFF;
                    font-weight: normal;
                    border-bottom: 1px solid #222;
                    padding: 0.5rem 1rem;
                }
                .sortable-item::before {
                    content: counter(item) ". ";
                    counter-increment: item;
                }
                """

                nova_ordem = sort_items(
                    [{'header': f'📋 Fila da {maquina}', 'items': elementos_drag}],
                    multi_containers=True,
                    custom_style=estilo_azul_escuro
                )

                col_sel1, col_sel2, col_sel3, col_salvar = st.columns([2, 2, 2, 2])

                with col_sel1:
                    propostas = ["--"] + sorted(set(item["proposta"] for item in fila))
                    proposta_selecionada = st.selectbox("Proposta", propostas, key=f"sel_proposta_{maquina}")

                with col_sel2:
                    materiais_filtrados = [
                        item["material"] for item in fila
                        if item["proposta"] == proposta_selecionada
                    ] if proposta_selecionada != "--" else []
                    materiais = ["--"] + sorted(set(materiais_filtrados))
                    material_selecionado = st.selectbox("Material", materiais, key=f"sel_material_{maquina}")

                with col_sel3:
                    espessuras_filtradas = [
                        item["espessura"] for item in fila
                        if item["proposta"] == proposta_selecionada and item["material"] == material_selecionado
                    ] if proposta_selecionada != "--" and material_selecionado != "--" else []
                    espessuras = ["--"] + sorted(set(espessuras_filtradas))
                    espessura_selecionada = st.selectbox("Espessura", espessuras, key=f"sel_espessura_{maquina}")

                with col_salvar:
                    if st.button("💾 Salvar Nova Ordem de Corte", key=f"salvar_ordem_{maquina}"):
                        nova_ordem_ids = [mapa_itens[label] for label in nova_ordem[0]["items"]]

                        if (
                            proposta_selecionada != "--" and
                            material_selecionado != "--" and
                            espessura_selecionada != "--"
                        ):
                            ids_prioritarios = [
                                item["id"]
                                for item in fila
                                if item["proposta"] == proposta_selecionada and
                                item["material"] == material_selecionado and
                                item["espessura"] == espessura_selecionada
                            ]
                            nova_ordem_ids = [id_ for id_ in nova_ordem_ids if id_ not in ids_prioritarios]
                            nova_ordem_ids = ids_prioritarios + nova_ordem_ids

                        # Atualiza posições no banco
                        for nova_posicao, id_item in enumerate(nova_ordem_ids):
                            supabase.table("fila_maquinas").update(
                                {"posicao": nova_posicao}
                            ).eq("id", id_item).execute()

                        st.success("Nova ordem de corte salva com sucesso.")
                        st.rerun()


        else:
            st.markdown("_Fila vazia_")

        st.divider()
        mostrar_grafico_eventos(maquina)
