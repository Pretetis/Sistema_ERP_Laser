import streamlit as st
from streamlit_sortables import sort_items
from streamlit import session_state as ss

import pandas as pd
import hashlib
from datetime import date
from pathlib import Path

from utils.supabase import supabase, excluir_imagem_supabase
from utils.extracao import extrair_dados_por_posicao
from utils.db import (
    obter_fila, registrar_evento, mostrar_grafico_eventos, excluir_trabalho_por_cnc,
    obter_corte_atual, iniciar_corte, finalizar_corte, cnc_ja_existe,
    retornar_para_pendentes, retomar_interrupcao, adicionar_na_fila,
    retornar_item_da_fila_para_pendentes, inserir_trabalho_pendente,
    obter_status_interrompido, atualizar_status_interrompido
)

def hash_grupo(grupo: str) -> str:
    return hashlib.md5(grupo.encode()).hexdigest()[:6]

@st.dialog("Interrupção de Corte")
def abrir_dialogo_interrupcao(maquina):
    nome = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    motivo = st.text_area("Motivo da Interrupção", key=f"motivo_{maquina}")
    if st.button("Confirmar Parada", key=f"confirmar_parada_{maquina}"):
        corte = obter_corte_atual(maquina)
        if corte:
            registrar_evento(maquina, "parado", corte["proposta"], corte["cnc"], motivo=motivo, nome=nome)
            atualizar_status_interrompido(maquina, True)  
            st.session_state[f"abrir_dialogo_{maquina}"] = False  
            st.success("Interrupção registrada.")
            st.rerun()

@st.fragment
def renderizar_maquina_fragment(maquina, modo="individual",gatilho=0):
    _ = gatilho  # força rerender
    # 👇 Esta linha é OBRIGATÓRIA: obriga o fragmento a reagir quando o valor mudar
    _ = st.session_state.get(f"gatilho_atualizacao_{maquina}", 0)

    dados_corte = obter_corte_atual(maquina)
    fila_maquina = obter_fila(maquina)
    exibir_maquina(maquina, modo=modo, dados_corte=dados_corte, fila_maquina=fila_maquina)

def exibir_maquina(maquina, modo="individual", dados_corte=None, fila_maquina=None):
    if st.session_state.get(f"status_corte_finalizado_{maquina}"):
        st.session_state[f"status_corte_finalizado_{maquina}"] = False
    usuario = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    cargo_usuario = st.session_state.get("usuario", {}).get("cargo", "")

    cargo_pcp = cargo_usuario in ["PCP", "Gerente"]
    cargo_operador = cargo_usuario in ["Operador", "Gerente"]
    cargo_empilhadeira = cargo_usuario in ["Empilhadeira", "Gerente"]
    key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
    key_base = f"{modo}_{maquina.replace(' ', '_')}"

    with st.container(border=True):
        st.markdown(f"## 🔧 {maquina}")

        corte = dados_corte if dados_corte is not None else obter_corte_atual(maquina)
        fila = fila_maquina if fila_maquina is not None else obter_fila(maquina)

        if corte:
            st.subheader(
                f"**🔹 Corte Atual:** x{corte.get('qtd_chapas', 'N/D')} | CNC {corte.get('cnc', 'N/D')} | "
                f"{corte.get('material', 'N/D')} | {corte.get('espessura', 'N/D')} mm"
            )

            if cargo_operador or cargo_pcp:
                interrompido = obter_status_interrompido(maquina)

                with st.container(border=True):
                    col_fim, col_intr, col_ret, col_pend = st.columns(4)

                if not interrompido:
                    with col_fim:
                        key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                        if st.button("✅ Finalizar Corte Atual", key=f"fim_{key_prefix}"):
                            corte_atual = obter_corte_atual(maquina)
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
                            st.session_state[f"status_corte_finalizado_{maquina}"] = True
                            st.rerun(scope="fragment")

                    with col_intr:
                        key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                        if st.button("⏸️ Parar Corte", key=f"parar_{key_prefix}"):
                            st.session_state[f"abrir_dialogo_{maquina}"] = True
                        if st.session_state.get(f"abrir_dialogo_{maquina}"):
                            abrir_dialogo_interrupcao(maquina)

                else:
                    with col_ret:
                        key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                        if st.button("▶️ Retomar Corte", key=f"retomar_{key_prefix}"):
                            retomar_interrupcao(maquina)
                            atualizar_status_interrompido(maquina, False)
                            st.success("Corte retomado.")
                            st.rerun(scope="fragment")

                with col_pend:
                    key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                    if st.button("🔁 Retornar para Pendentes", key=f"ret_{key_prefix}"):
                        retornar_para_pendentes(maquina)
                        st.success("Trabalho retornado para pendentes")
                        fn_pendentes = ss.get("atualizar_trabalhos_pendentes_fn")
                        if fn_pendentes:
                            fn_pendentes()
                        st.rerun(scope="fragment")
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
                if st.session_state.get(f"status_salvo_local_{maquina}"):
                    st.success("Local separado salvo com sucesso.")
                    st.session_state[f"status_salvo_local_{maquina}"] = False

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
                    if st.button(f"💾 Salvar 'Local Separado' - {maquina}", key=f"btn_salvar_local_{modo}_{maquina}"):
                        updates = []
                        for idx, novo_valor in enumerate(edited_df["Local Separado"]):
                            id_item = dados_fila[idx]["ID"]
                            if novo_valor != dados_fila[idx]["Local Separado"]:
                                updates.append({
                                    "id": id_item,
                                    "local_separado": novo_valor
                                })

                        for update in updates:
                            supabase.table("fila_maquinas").update({
                                "local_separado": update["local_separado"],
                                "modificado_por": usuario
                            }).eq("id", update["id"]).execute()
                        st.success("Campos salvos com sucesso.")
                        st.session_state[f"status_salvo_local_{maquina}"] = True

                opcoes = {
                    f"{item['proposta']} | CNC {item['cnc']}": item['id']
                    for item in fila
                }
                if cargo_operador or cargo_pcp:
                    key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                    escolha = st.selectbox("Escolha o próximo CNC:", list(opcoes.keys()), key=f"escolha_{modo}_{maquina}")
                    col_iniciar, col_ret = st.columns(2)
                    with col_iniciar:
                        key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                        if st.button("▶️ Iniciar Corte", key=f"iniciar_{modo}_{maquina}"):
                            if corte:
                                st.warning("Finalize o corte atual antes de iniciar um novo.")
                            else:
                                iniciar_corte(maquina, opcoes[escolha])
                                st.rerun(scope="fragment")

                    with col_ret:
                        key_prefix = f"{modo}_{maquina.replace(' ', '_')}"
                        if st.button("🔁 Retornar CNC para Pendentes", key=f"ret_fila_{modo}_{maquina}"):
                            retornar_item_da_fila_para_pendentes(opcoes[escolha])
                            st.success("Item da fila retornado para pendentes.")

                            fn_pendentes = ss.get("atualizar_trabalhos_pendentes_fn")
                            if fn_pendentes:
                                fn_pendentes()
                            st.rerun(scope="fragment")

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
                        proposta_selecionada = st.selectbox("Proposta", propostas, key=f"sel_proposta_{modo}_{maquina}")

                    with col_sel2:
                        materiais_filtrados = [
                            item["material"] for item in fila
                            if item["proposta"] == proposta_selecionada
                        ] if proposta_selecionada != "--" else []
                        materiais = ["--"] + sorted(set(materiais_filtrados))
                        material_selecionado = st.selectbox("Material", materiais, key=f"sel_material_{modo}_{maquina}")

                    with col_sel3:
                        espessuras_filtradas = [
                            item["espessura"] for item in fila
                            if item["proposta"] == proposta_selecionada and item["material"] == material_selecionado
                        ] if proposta_selecionada != "--" and material_selecionado != "--" else []
                        espessuras = ["--"] + sorted(set(espessuras_filtradas))
                        espessura_selecionada = st.selectbox("Espessura", espessuras, key=f"sel_espessura_{modo}_{maquina}")

                    with col_salvar:
                        if st.button("💾 Salvar Nova Ordem de Corte", key=f"salvar_ordem_{modo}_{maquina}"):
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
                                item_original = next((f for f in fila if f["id"] == id_item), None)
                                if item_original and item_original.get("posicao", -1) != nova_posicao:
                                    supabase.table("fila_maquinas").update(
                                        {"posicao": nova_posicao}
                                    ).eq("id", id_item).execute()

                            st.success("Nova ordem de corte salva com sucesso.")
                            st.rerun()


        else:
            st.divider()
            st.markdown("_Fila vazia_")

    with st.expander("Gerar Gráfico da Máquina", expanded=True):
        mostrar_grafico_eventos(maquina)

@st.dialog("Substituir CNC Existente")
def confirmar_substituicao_cnc(dados_trabalho):
    cnc = dados_trabalho["cnc"]
    st.warning(f"O CNC '{cnc}' já está cadastrado. Deseja substituí-lo?")
    
    with st.container(border=True):
        st.write(f"**Proposta:** {dados_trabalho['proposta']}")
        st.write(f"**Material:** {dados_trabalho['material']}")
        st.write(f"**Espessura:** {dados_trabalho['espessura']} mm")
        st.write(f"**Qtd Chapas:** {dados_trabalho['qtd_chapas']}")
        st.write(f"**Tempo Total:** {dados_trabalho['tempo_total']}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirmar Substituição", key=f"confirmar_sub_{cnc}"):
            excluir_trabalho_por_cnc(cnc)
            inserir_trabalho_pendente(dados_trabalho)
            st.success(f"CNC '{cnc}' substituído com sucesso!")
            st.rerun()
    with col2:
        if st.button("❌ Cancelar", key=f"cancelar_sub_{cnc}"):
            st.info("Substituição cancelada.")
            st.rerun()


def processar_pdfs(pdfs):
    if "cnc_para_confirmar" not in st.session_state:
        st.session_state["cnc_para_confirmar"] = []

    for pdf in pdfs:
        info = extrair_dados_por_posicao(pdf)
        if not info:
            continue

        cnc = Path(pdf.name).stem
        tempo_td = pd.to_timedelta(info["tempo_total"]) if isinstance(info["tempo_total"], str) else info["tempo_total"]
        total_segundos = int(tempo_td.total_seconds())
        tempo_formatado = f"{total_segundos // 3600:02}:{(total_segundos % 3600) // 60:02}:{total_segundos % 60:02}"

        dados_trabalho = {
            "grupo": f"{info['proposta']}-{int(round(info['espessura']*100)):04d}-{info['material']}",
            "proposta": info["proposta"],
            "espessura": info["espessura"],
            "material": info["material"],
            "cnc": cnc,
            "programador": info["programador"],
            "qtd_chapas": info["qtd_chapas"],
            "tempo_total": tempo_formatado,
            "caminho": info["caminho"],
            "data_prevista": date.today().isoformat(),
            "processos": [],
            "autorizado": False,
            "gas": []
        }

        if cnc_ja_existe(cnc):
            # Salva em memória para renderizar o diálogo depois
            st.session_state["cnc_para_confirmar"].append(dados_trabalho)
        else:
            inserir_trabalho_pendente(dados_trabalho)

# Em auxiliares.py ou onde preferir
MAQUINAS = ["LASER 1", "LASER 2", "LASER 3", "LASER 4", "LASER 5", "LASER 6"]
from utils.db import adicionar_na_fila

def modal_enviar_cnc(item):
    from utils.supabase import supabase  # garantir que está importado

    usuario = st.session_state.get("usuario", {}).get("nome", "desconhecido")
    item_id = item.get("id", "desconhecido")  # fallback caso não tenha id

    maquina_escolhida = st.selectbox(
        "Selecione a máquina",
        MAQUINAS,
        key=f"modal_sel_maquina_{item_id}"
    )

    if st.button("🚀 Confirmar envio", key=f"modal_btn_confirmar_envio_{item_id}"):
        adicionar_na_fila(maquina_escolhida, {
            "proposta": item["proposta"],
            "cnc": item["cnc"],
            "material": item["material"],
            "espessura": item["espessura"],
            "qtd_chapas": int(item["qtd_chapas"]),
            "tempo_total": item["tempo_total"],
            "caminho": item["caminho"],
            "programador": item.get("programador", "DESCONHECIDO"),
            "processos": item.get("processos", []),
            "gas": item.get("gas", None),
            "data_prevista": item["data_prevista"]
        }, usuario)

        # Remove apenas o CNC individual das pendências
        supabase.table("trabalhos_pendentes") \
            .delete() \
            .eq("id", item_id) \
            .execute()

        # Atualiza interface
        fn_maquina = st.session_state.get(f"atualizar_maquina_fn_{maquina_escolhida}")
        if fn_maquina:
            fn_maquina()
        # Remove do modal imediatamente
        st.session_state["modal_cnc_item"] = None

        # Atualiza trabalhos pendentes
        st.session_state["atualizar_trabalhos_pendentes"] = st.session_state.get("atualizar_trabalhos_pendentes", 0) + 1
        st.rerun(scope="fragment")

@st.fragment
def renderizar_trabalhos_pendentes(gatilho=0):
    from collections import defaultdict
    from utils.db import excluir_trabalhos_grupo, adicionar_na_fila
    from utils.supabase import supabase, excluir_imagem_supabase
    from streamlit import session_state as ss

    contador = st.session_state.get("atualizar_trabalhos_pendentes", 0)
    _ = gatilho
    usuario = ss.get("usuario", {}).get("nome", "desconhecido")
    cargo_usuario = ss.get("usuario", {}).get("cargo", "")
    cargo_pcp = cargo_usuario in ["PCP", "Gerente"]
    cargo_operador = cargo_usuario in ["Operador", "PCP", "Gerente"]

    MAQUINAS = ["LASER 1", "LASER 2", "LASER 3", "LASER 4", "LASER 5", "LASER 6"]

    trabalhos_raw = (
        supabase.table("trabalhos_pendentes")
        .select("id,grupo,proposta,espessura,material,tempo_total,qtd_chapas,"
                "programador,caminho,data_prevista,processos,gas,cnc")
        .eq("autorizado", True)
        .execute()
        .data or []
    )

    grupos = defaultdict(list)
    for t in trabalhos_raw:
        grupos[t["grupo"]].append(t)

    grupo_sucesso = ss.get("status_envio_grupo")
    if grupo_sucesso in grupos:
        del grupos[grupo_sucesso]
        ss["status_envio_grupo"] = None

    for idx, (grupo, itens) in enumerate(grupos.items()):
        grupo_hash = hash_grupo(grupo)
        trabalho = itens[0]

        titulo_linha1 = (
            f"🔹 {trabalho.get('proposta', 'N/D')} | {trabalho.get('espessura', 'N/D')} mm | "
            f"{trabalho.get('material', 'N/D')} | x{len(itens)} CNCs | ⏱ {trabalho.get('tempo_total', 'N/D')}"
        )
        data_fmt = "/".join(reversed(trabalho["data_prevista"].split("-")))
        gas_fmt = f"💨 {trabalho.get('gas')}" if trabalho.get("gas") else ""
        titulo_linha2 = f"📅 {data_fmt} | ⚙️ {trabalho.get('processos')} | {gas_fmt}"
        titulo = f"{titulo_linha1}\n\n{titulo_linha2}"

        with st.expander(titulo, expanded=False):
            if cargo_pcp or cargo_operador:
                maquina_escolhida = st.selectbox(
                    "Enviar todos para:",
                    MAQUINAS,
                    key=f"sel_maquina_{idx}_{grupo_hash}"
                )

                col_add, col_del = st.columns(2)
                with col_add:
                    if st.button(
                        "➕ Enviar todos para a máquina",
                        key=f"btn_add_todos_{idx}_{grupo_hash}"
                    ):
                        trabalhos_para_enviar = []
                        ids_para_deletar = []
                        for item in itens:
                            trabalhos_para_enviar.append({
                                "proposta": item["proposta"],
                                "cnc": item["cnc"],
                                "material": item["material"],
                                "espessura": item["espessura"],
                                "qtd_chapas": int(item["qtd_chapas"]),
                                "tempo_total": item["tempo_total"],
                                "caminho": item["caminho"],
                                "programador": item.get("programador", "DESCONHECIDO"),
                                "processos": item.get("processos", []),
                                "gas": item.get("gas", None),
                                "data_prevista": item["data_prevista"]
                            })
                            ids_para_deletar.append(item["id"])

                        adicionar_na_fila(maquina_escolhida, trabalhos_para_enviar, usuario)
                        supabase.table("trabalhos_pendentes").delete().in_("id", ids_para_deletar).execute()
                        ss["status_envio_grupo"] = grupo

                        ss["atualizar_trabalhos_pendentes"] = ss.get("atualizar_trabalhos_pendentes", 0) + 1
                        fn_pendentes = ss.get("atualizar_trabalhos_pendentes_fn")
                        if fn_pendentes:
                            fn_pendentes()

                        fn_maquina = ss.get(f"atualizar_maquina_fn_{maquina_escolhida}")
                        if fn_maquina:
                            fn_maquina()
                        
                        st.rerun(scope="fragment")

                with col_del:
                    if st.button(
                        "🖑 Excluir Trabalho",
                        key=f"del_{idx}_{grupo_hash}"  
                    ):
                        for trabalho in itens:
                            caminho = trabalho.get("caminho")
                            if caminho:
                                excluir_imagem_supabase(caminho)
                        excluir_trabalhos_grupo(grupo)
                        
                        if "atualizar_trabalhos_pendentes_fn" in ss:
                            ss["atualizar_trabalhos_pendentes_fn"]()
                        st.success("Trabalho excluído.")
                        st.rerun(scope="fragment")

            for i, item in enumerate(itens):
                with st.container(border=True):
                    col1, col2 = st.columns([2, 2])
                    with col1:
                        st.markdown(f"**Programador:** {item['programador']}")
                        st.markdown(f"**CNC:** {item['cnc']}")
                        st.markdown(f"**Qtd Chapas:** {item['qtd_chapas']}")
                        st.markdown(f"**Tempo Total:** {item['tempo_total']}")
                        if cargo_pcp or cargo_operador:
                            with st.container(border=False):
                                st.write("📄 Enviar CNC para Máquina")
                                modal_enviar_cnc(item)
                    with col2:
                        if item["caminho"].startswith("http"):
                            st.image(item["caminho"], caption=f"CNC {item['cnc']}", use_container_width=True)
                        else:
                            st.warning("Imagem não encontrada.")
    item_modal = ss.get("modal_cnc_item")
    if item_modal and not ss.get("rerun_do_modal"):
        ss["rerun_do_modal"] = True
        modal_enviar_cnc(item_modal)
    elif ss.get("rerun_do_modal"):
        ss["modal_cnc_item"] = None
        ss["rerun_do_modal"] = False