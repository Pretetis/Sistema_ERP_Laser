from utils.supabase import supabase
from datetime import datetime

from utils.supabase import upload_txt_to_supabase, baixar_txt_conteudo


def adicionar_na_fila(maquina, trabalho):
    supabase.table("fila_maquinas").insert({
        "maquina": maquina,
        "proposta": trabalho["Proposta"],
        "cnc": trabalho["CNC"],
        "material": trabalho["Material"],
        "espessura": trabalho["Espessura"],
        "quantidade": trabalho["Quantidade"],
        "tempo_total": trabalho["Tempo Total"],
        "caminho": trabalho.get("Caminho", "")
    }).execute()


def registrar_trabalho_enviado(grupo, proposta, cnc, material, espessura,
                               quantidade, tempo_total, programador,
                               data_prevista=None, processos=None):
    supabase.table("trabalhos_enviados").upsert({
        "grupo": grupo,
        "proposta": proposta,
        "cnc": cnc,
        "material": material,
        "espessura": espessura,
        "quantidade": quantidade,
        "tempo_total": tempo_total,
        "programador": programador,
        "data_prevista": data_prevista,
        "processos": processos
    }).execute()


def obter_fila(maquina):
    res = supabase.table("fila_maquinas").select("*").eq("maquina", maquina).execute()
    return res.data if res.data else []


def obter_corte_atual(maquina):
    res = supabase.table("corte_atual").select("*").eq("maquina", maquina).execute()
    return res.data[0] if res.data else None


def iniciar_corte(maquina, id_fila):
    fila = supabase.table("fila_maquinas").select("*").eq("id", id_fila).execute()
    if not fila.data:
        return

    item = fila.data[0]

    supabase.table("fila_maquinas").delete().eq("id", id_fila).execute()

    supabase.table("corte_atual").upsert({
        "maquina": item["maquina"],
        "proposta": item["proposta"],
        "cnc": item["cnc"],
        "material": item["material"],
        "espessura": item["espessura"],
        "quantidade": item["quantidade"],
        "tempo_total": item["tempo_total"]
    }).execute()


def finalizar_corte(maquina):
    atual = obter_corte_atual(maquina)
    if not atual:
        return

    if atual["quantidade"] > 1:
        supabase.table("corte_atual").update({"quantidade": atual["quantidade"] - 1}).eq("maquina", maquina).execute()
    else:
        supabase.table("corte_atual").delete().eq("maquina", maquina).execute()


def excluir_da_fila(maquina, id_trabalho):
    supabase.table("fila_maquinas").delete().eq("maquina", maquina).eq("id", id_trabalho).execute()


def excluir_do_corte(maquina):
    supabase.table("corte_atual").delete().eq("maquina", maquina).execute()


def excluir_pendente(grupo):
    # Nada a fazer na base supabase, pois arquivo .txt é quem representa pendência
    pass

def retornar_para_pendentes(maquina):
    atual = obter_corte_atual(maquina)
    if not atual:
        return

    grupo = f"{atual['proposta']}-{int(atual['espessura'] * 100):04}-{atual['material']}"

    res = supabase.table("trabalhos_enviados").select("programador", "data_prevista", "processos").eq("grupo", grupo).eq("cnc", atual["cnc"]).execute()
    dados = res.data[0] if res.data else {}

    conteudo = f"""Programador: {dados.get('programador', 'DESCONHECIDO')}
CNC: {atual['cnc']}
Qtd Chapas: {atual['quantidade']}
Tempo Total: {atual['tempo_total']}
Caminho: CNC/{atual['cnc']}.pdf

===== INFORMAÇÕES ADICIONAIS =====
Data prevista: {dados.get('data_prevista', str(datetime.today().date()))}
Processos: {dados.get('processos', 'Corte Retornado')}
"""

    upload_txt_to_supabase(f"{grupo}.txt", conteudo, pasta="trabalhos_pendentes")
    excluir_do_corte(maquina)


def retornar_item_da_fila_para_pendentes(id_trabalho):
    res = supabase.table("fila_maquinas").select("*").eq("id", id_trabalho).execute()
    if not res.data:
        return

    item = res.data[0]
    grupo = f"{item['proposta']}-{int(item['espessura'] * 100):04}-{item['material']}"

    dados_res = supabase.table("trabalhos_enviados").select("programador", "data_prevista", "processos").eq("grupo", grupo).eq("cnc", item["cnc"]).execute()
    dados = dados_res.data[0] if dados_res.data else {}

    try:
        conteudo_atual = baixar_txt_conteudo(f"{grupo}.txt", pasta="trabalhos_pendentes")
    except Exception:
        conteudo_atual = ""

    caminho_img = item.get("caminho", f"CNC/{item['cnc']}")
    novo_bloco = f"""Programador: {dados.get('programador', 'DESCONHECIDO')}
CNC: {item['cnc']}
Qtd Chapas: {item['quantidade']}
Tempo Total: {item['tempo_total']}
Caminho: {caminho_img}"""

    if "===== INFORMAÇÕES ADICIONAIS =====" in conteudo_atual:
        partes = conteudo_atual.split("===== INFORMAÇÕES ADICIONAIS =====")
        principal = partes[0].strip()
        adicionais = partes[1].strip()
        novo_conteudo = f"{principal}\n\n{novo_bloco}\n\n===== INFORMAÇÕES ADICIONAIS =====\n{adicionais}"
    else:
        novo_conteudo = f"{conteudo_atual.strip()}\n\n{novo_bloco}"
        novo_conteudo += f"\n\n===== INFORMAÇÕES ADICIONAIS =====\nData prevista: {dados.get('data_prevista', str(datetime.today().date()))}\nProcessos: {dados.get('processos', 'Corte Retornado')}"

    upload_txt_to_supabase(f"{grupo}.txt", novo_conteudo, pasta="trabalhos_pendentes")
    excluir_da_fila(item["maquina"], id_trabalho)


def atualizar_quantidade(maquina, nova_quantidade):
    supabase.table("corte_atual").update({"quantidade": nova_quantidade}).eq("maquina", maquina).execute()