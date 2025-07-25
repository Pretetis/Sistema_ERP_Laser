import streamlit as st
import pandas as pd
from streamlit_sortables import sort_items

from utils.supabase import supabase, excluir_imagem_supabase
from utils.db import (
    obter_fila, registrar_evento, mostrar_grafico_eventos,
    obter_corte_atual, iniciar_corte, finalizar_corte,
    retornar_para_pendentes, retomar_interrupcao,
    retornar_item_da_fila_para_pendentes
)

@st.dialog("Interrupção de Corte")
def abrir_dialogo_interrupcao(maquina):
    usuario = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    motivo = st.text_area("Motivo da Interrupção", key=f"motivo_{maquina}")
    if st.button("Confirmar Parada", key=f"confirmar_parada_{maquina}"):
        corte = obter_corte_atual(maquina)
        if corte:
            registrar_evento(maquina, "parado", corte["proposta"], corte["cnc"], motivo=motivo, usuario=usuario)
            st.success("Interrupção registrada.")
            st.rerun()

def exibir_maquina(maquina, modo="individual"):
    usuario = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    cargo_usuario = st.session_state.get("usuario", {}).get("cargo", "")

    cargo_pcp = cargo_usuario in ["PCP", "Gerente"]
    cargo_operador = cargo_usuario in ["Operador", "Gerente"]
    cargo_empilhadeira = cargo_usuario in ["Empilhadeira", "Gerente"]
    key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
    key_base = f"{modo}_{maquina.replace(' ', '_')}"

    with st.container(border=True):
        st.markdown(f"## 🔧 {maquina}")

        corte = obter_corte_atual(maquina)
        fila = obter_fila(maquina)  # já vem ordenada por 'posicao'

        if corte:
            st.subheader(
                f"**🔹 Corte Atual:** x{corte.get('qtd_chapas', 'N/D')} | CNC {corte.get('cnc', 'N/D')} | "
                f"{corte.get('material', 'N/D')} | {corte.get('espessura', 'N/D')} mm"
            )

            if cargo_operador or cargo_pcp:
                with st.container(border=True):
                    col_fim, col_intr, col_ret, col_pend = st.columns(4)

                with col_fim:
                    key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                    if st.button("✅ Finalizar Corte Atual", key=f"fim_{key_prefix}"):
                        corte_atual = obter_corte_atual(maquina)

                        # Garantir que sempre trabalhamos com lista
                        if not isinstance(corte_atual, list):
                            corte_atual = [corte_atual]

                        for trabalho in corte_atual:
                            if isinstance(trabalho, dict):
                                caminho = trabalho.get("caminho")
                                if caminho:
                                    excluir_imagem_supabase(caminho)
                            elif isinstance(trabalho, str) and trabalho.startswith("http"):
                                excluir_imagem_supabase(trabalho)

                        finalizar_corte(maquina, usuario)
                        st.success("Corte finalizado")
                        st.rerun()

                    with col_intr:
                        key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                        if st.button("⏸️ Parar Corte", key=f"parar_{key_prefix}"):
                            abrir_dialogo_interrupcao(maquina)

                    with col_ret:
                        key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                        if st.button("▶️ Retomar Corte", key=f"retomar_{key_prefix}"):
                            retomar_interrupcao(maquina)
                            st.success("Corte retomado.")
                            st.rerun()

                    with col_pend:
                        key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                        if st.button("🔁 Retornar para Pendentes", key=f"ret_{key_prefix}"):
                            retornar_para_pendentes(maquina)
                            st.success("Trabalho retornado para pendentes")
                            st.rerun()
        else:
            st.markdown("_Nenhum corte em andamento_")

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
                        "Local Separado": item.get("local_separado", ""),
                        "Gás": item.get("gas", "")
                    })

                df_visual = pd.DataFrame(dados_fila)

                config = {
                    "Caminho": st.column_config.ImageColumn(),
                    "Local Separado": st.column_config.TextColumn(disabled=not cargo_empilhadeira)
                }

                for col in df_visual.columns:
                    if col not in ["Local Separado", "Caminho"]:
                        config[col] = st.column_config.TextColumn(disabled=True)

                edited_df = st.data_editor(
                    df_visual.drop(columns=["ID", "Máquina"]),
                    column_config=config,
                    hide_index=True,
                    use_container_width=True,
                    key=f"data_editor_{key_prefix}"
                )

                if cargo_empilhadeira:
                    if st.button(f"💾 Salvar 'Local Separado' - {maquina}"):
                        for idx, novo_valor in enumerate(edited_df["Local Separado"]):
                            id_item = dados_fila[idx]["ID"]
                            supabase.table("fila_maquinas").update({
                                    "local_separado": novo_valor,
                                    "modificado_por": usuario
                                }).eq("id", id_item).execute()
                        st.success("Campos salvos com sucesso.")
                        st.rerun()

                opcoes = {
                    f"{item['proposta']} | CNC {item['cnc']}": item['id']
                    for item in fila
                }
                if cargo_operador or cargo_pcp:
                    key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                    escolha = st.selectbox("Escolha o próximo CNC:", list(opcoes.keys()), key=f"escolha_{key_prefix}")
                    col_iniciar, col_ret = st.columns(2)
                    with col_iniciar:
                        key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                        if st.button("▶️ Iniciar Corte", key=f"iniciar_{key_prefix}"):
                            if corte:
                                st.warning("Finalize o corte atual antes de iniciar um novo.")
                            else:
                                iniciar_corte(maquina, opcoes[escolha])
                                st.success("Corte iniciado.")
                                st.rerun()

                    with col_ret:
                        key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                        if st.button("🔁 Retornar CNC para Pendentes", key=f"ret_fila_{key_prefix}"):
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
                    custom_style=estilo_azul_escuro,
                    key=f"sortable_{key_base}"  # <- chave única aqui
                )

                if cargo_pcp:
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
            st.divider()
            st.markdown("_Fila vazia_")

        st.divider()
        mostrar_grafico_eventos(maquina)