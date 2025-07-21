from utils.supabase import supabase
from datetime import datetime

def inserir_trabalho_pendente(dados):
    supabase.table("trabalhos_pendentes").insert(dados).execute()

def adicionar_na_fila(maquina, trabalho):
    supabase.table("fila_maquinas").insert({
        "maquina": maquina,
        "proposta": trabalho["proposta"],
        "cnc": trabalho["cnc"],
        "material": trabalho["material"],
        "espessura": trabalho["espessura"],
        "quantidade": trabalho["quantidade"],
        "tempo_total": trabalho["tempo_total"],
        "caminho": trabalho.get("caminho", "")
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

def retornar_para_pendentes(maquina):
    atual = obter_corte_atual(maquina)
    if not atual:
        return

    grupo = f"{atual['proposta']}-{int(atual['espessura'] * 100):04}-{atual['material']}"

    res = supabase.table("trabalhos_pendentes")\
        .select("programador", "data_prevista", "processos")\
        .eq("grupo", grupo)\
        .eq("cnc", atual["cnc"]).execute()

    dados = res.data[0] if res.data else {}

    trabalho = {
        "grupo": grupo,
        "proposta": atual["proposta"],
        "cnc": atual["cnc"],
        "material": atual["material"],
        "espessura": atual["espessura"],
        "quantidade": atual["quantidade"],
        "tempo_total": atual["tempo_total"],
        "programador": dados.get("programador", "DESCONHECIDO"),
        "data_prevista": dados.get("data_prevista", str(datetime.today().date())),
        "processos": dados.get("processos", "Corte Retornado"),
        "autorizado": False,
        "caminho": atual.get("caminho", f"CNC/{atual['cnc']}.pdf")
    }

    inserir_trabalho_pendente(trabalho)
    excluir_do_corte(maquina)

def retornar_item_da_fila_para_pendentes(id_trabalho):
    res = supabase.table("fila_maquinas").select("*").eq("id", id_trabalho).execute()
    if not res.data:
        return

    item = res.data[0]
    grupo = f"{item['proposta']}-{int(item['espessura'] * 100):04}-{item['material']}"
    cnc_alvo = item["cnc"]

    dados_res = supabase.table("trabalhos_pendentes")\
        .select("programador", "data_prevista", "processos")\
        .eq("grupo", grupo)\
        .eq("cnc", cnc_alvo).execute()

    dados = dados_res.data[0] if dados_res.data else {}

    novo_trabalho = {
        "grupo": grupo,
        "proposta": item["proposta"],
        "cnc": item["cnc"],
        "material": item["material"],
        "espessura": item["espessura"],
        "quantidade": item["quantidade"],
        "tempo_total": item["tempo_total"],
        "programador": dados.get("programador", "DESCONHECIDO"),
        "data_prevista": dados.get("data_prevista", str(datetime.today().date())),
        "processos": dados.get("processos", "Corte Retornado"),
        "autorizado": False,
        "caminho": item.get("caminho", f"CNC/{item['cnc']}.pdf")
    }

    inserir_trabalho_pendente(novo_trabalho)
    excluir_da_fila(item["maquina"], id_trabalho)

def atualizar_quantidade(maquina, nova_quantidade):
    supabase.table("corte_atual").update({"quantidade": nova_quantidade}).eq("maquina", maquina).execute()


def atualizar_trabalho_pendente(cnc, grupo, tempo_total, data_prevista=None, processos=None, autorizado=False):
    update_data = {
        "tempo_total": tempo_total,
        "data_prevista": data_prevista,
        "processos": processos,
        "autorizado": autorizado
    }

    # Remove campos nulos para evitar sobrescrita
    update_data = {k: v for k, v in update_data.items() if v is not None}

    supabase.table("trabalhos_pendentes")\
        .update(update_data)\
        .eq("grupo", grupo)\
        .eq("cnc", cnc)\
        .execute()

def excluir_trabalhos_grupo(grupo: str):
    supabase.table("trabalhos_pendentes")\
        .delete()\
        .eq("grupo", grupo)\
        .execute()