from utils.supabase import supabase
from datetime import datetime, timedelta

def inserir_trabalho_pendente(dados):
    supabase.table("trabalhos_pendentes").insert(dados).execute()

def adicionar_na_fila(maquina, trabalho):
    supabase.table("fila_maquinas").insert({
        "maquina": maquina,
        "proposta": trabalho["proposta"],
        "cnc": trabalho["cnc"],
        "material": trabalho["material"],
        "espessura": trabalho["espessura"],
        "qtd_chapas": int(trabalho["qtd_chapas"]),
        "tempo_total": trabalho["tempo_total"],
        "caminho": trabalho.get("caminho", ""),
        "programador": trabalho["programador"],
        "processos": normalizar_processos(trabalho.get("processos"))
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
        "qtd_chapas": int(item["qtd_chapas"]),
        "tempo_total": item["tempo_total"],
        "caminho": item["caminho"],
        "programador": item["programador"],
        "processos": item.get("processos")
    }).execute()

    registrar_evento(maquina, "iniciado", item["proposta"], item["cnc"])

def finalizar_corte(maquina):
    atual = obter_corte_atual(maquina)
    if not atual:
        return

    qtd_chapas = atual["qtd_chapas"]
    if qtd_chapas <= 0:
        excluir_do_corte(maquina)
        return

    # Tempo total atual em string "HH:MM:SS" => timedelta
    tempo_total_str = atual["tempo_total"]
    h, m, s = map(int, tempo_total_str.split(":"))
    tempo_total = timedelta(hours=h, minutes=m, seconds=s)

    # Recalcula tempo restante proporcionalmente
    tempo_por_chapa = tempo_total / qtd_chapas
    novo_qtd_chapas = qtd_chapas - 1

    if novo_qtd_chapas > 0:
        novo_tempo = tempo_por_chapa * novo_qtd_chapas
        novo_tempo_str = timedelta_to_hms_string(novo_tempo)

        supabase.table("corte_atual").update({
            "qtd_chapas": novo_qtd_chapas,
            "tempo_total": novo_tempo_str
        }).eq("maquina", maquina).execute()
    else:
        excluir_do_corte(maquina)

    registrar_evento(maquina, "finalizado", atual["proposta"], atual["cnc"])

def excluir_da_fila(maquina, id_trabalho):
    supabase.table("fila_maquinas").delete().eq("maquina", maquina).eq("id", id_trabalho).execute()


def excluir_do_corte(maquina):
    supabase.table("corte_atual").delete().eq("maquina", maquina).execute()

def retornar_para_pendentes(maquina):
    atual = obter_corte_atual(maquina)
    if not atual:
        return

    grupo = f"{atual['proposta']}-{int(atual['espessura'] * 100):04}-{atual['material']}"

    trabalho = {
        "grupo": grupo,
        "proposta": atual["proposta"],
        "cnc": atual["cnc"],
        "material": atual["material"],
        "espessura": atual["espessura"],
        "qtd_chapas": int(atual["qtd_chapas"]),
        "tempo_total": atual["tempo_total"],
        "programador": atual.get("programador", "DESCONHECIDO"),
        "data_prevista": str(datetime.today().date()),
        "processos": normalizar_processos(atual.get("processos")),
        "autorizado": True,
        "caminho": atual.get("caminho", f"CNC/{atual['cnc']}.pdf")
    }

    inserir_trabalho_pendente(trabalho)
    excluir_do_corte(maquina)

    registrar_evento(maquina, "cancelado", atual["proposta"], atual["cnc"])

def retornar_item_da_fila_para_pendentes(id_trabalho):
    res = supabase.table("fila_maquinas").select("*").eq("id", id_trabalho).execute()
    if not res.data:
        return

    item = res.data[0]
    grupo = f"{item['proposta']}-{int(item['espessura'] * 100):04}-{item['material']}"

    novo_trabalho = {
        "grupo": grupo,
        "proposta": item["proposta"],
        "cnc": item["cnc"],
        "material": item["material"],
        "espessura": item["espessura"],
        "qtd_chapas": int(item["qtd_chapas"]),
        "tempo_total": item["tempo_total"],
        "programador": item.get("programador", "DESCONHECIDO"),
        "data_prevista": str(datetime.today().date()),
        "processos": normalizar_processos(item.get("processos")),
        "autorizado": True,
        "caminho": item.get("caminho", f"CNC/{item['cnc']}.pdf")
    }

    inserir_trabalho_pendente(novo_trabalho)
    excluir_da_fila(item["maquina"], id_trabalho)


def atualizar_quantidade(maquina, nova_quantidade):
    supabase.table("corte_atual").update({"qtd_chapas": nova_quantidade}).eq("maquina", maquina).execute()


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
    
def timedelta_to_hms_string(td):
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def normalizar_processos(val):
    if isinstance(val, list) and val:
        return val
    return ["Corte Retornado"]

def retomar_interrupcao(maquina):
    res = supabase.table("eventos_corte")\
        .select("*")\
        .eq("maquina", maquina)\
        .eq("tipo_evento", "parado")\
        .is_("tempo_total", None)\
        .order("timestamp", desc=True)\
        .limit(1)\
        .execute()

    if res.data:
        parada = res.data[0]
        inicio = datetime.fromisoformat(parada["timestamp"])
        fim = datetime.now()
        duracao = fim - inicio

        registrar_evento(maquina, "retomado", parada["proposta"], parada["cnc"], tempo_total=str(duracao))

def registrar_evento(maquina, tipo_evento, proposta, cnc, motivo=None, tempo_total=None):
    supabase.table("eventos_corte").insert({
        "maquina": maquina,
        "proposta": proposta,
        "cnc": cnc,
        "tipo_evento": tipo_evento,
        "timestamp": datetime.now().isoformat(),
        "motivo": motivo,
        "tempo_total": tempo_total
    }).execute()