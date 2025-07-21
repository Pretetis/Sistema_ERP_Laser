from pathlib import Path
import pandas as pd
import re

from utils.supabase import listar_txts_supabase, baixar_txt_conteudo

# Caso queira separar categorias por prefixo no nome dos arquivos no Supabase:
PREFIXOS_CATEGORIAS = {
    "aguardando_aprovacao": "aguardando_aprovacao",
    "trabalhos_pendentes": "trabalhos_pendentes"
}

def carregar_trabalhos():
    trabalhos = {
        "aguardando_aprovacao": [],
        "trabalhos_pendentes": []
    }

    for categoria in ["aguardando_aprovacao", "trabalhos_pendentes"]:
        registros = []
        infos_adicionais = {}

        prefixo = PREFIXOS_CATEGORIAS[categoria]
        todos_arquivos = listar_txts_supabase(prefixo)
        arquivos_categoria = [arq for arq in todos_arquivos if arq.startswith(prefixo)]

        for nome_arquivo in arquivos_categoria:
            partes_nome = Path(nome_arquivo).stem.split("-")
            if len(partes_nome) < 3:
                continue

            chave_grupo = "-".join(partes_nome[:3])
            try:
                relativo = nome_arquivo.replace(f"{prefixo}/", "")
                conteudo = baixar_txt_conteudo(relativo, pasta=prefixo)
            except Exception:
                continue

            todos_blocos = re.split(r"\n\s*\n", conteudo.strip())
            blocos = [b for b in todos_blocos if "Programador:" in b and "===== INFORMAÇÕES ADICIONAIS" not in b]


            for bloco in blocos:
                dados = {}
                for linha in bloco.strip().splitlines():
                    if ":" in linha:
                        k, v = linha.split(":", 1)
                        dados[k.strip()] = v.strip()

                if dados.get("CNC"):
                    registros.append({
                        "Grupo": chave_grupo,
                        "Proposta": partes_nome[0],
                        "Espessura": float(partes_nome[1]) / 100,
                        "Material": partes_nome[2],
                        "CNC": dados.get("CNC", "").replace(".pdf", ""),
                        "Programador": dados.get("Programador", ""),
                        "Qtd Chapas": dados.get("Qtd Chapas", "1"),
                        "Tempo Total": dados.get("Tempo Total", ""),
                        "Caminho": dados.get("Caminho", "")
                    })

        df = pd.DataFrame(registros)
        if df.empty:
            continue

        trabalhos_categoria = []
        for grupo_nome, subdf in df.groupby("Grupo"):
            # Corrigir milissegundos para pandas aceitar corretamente
            subdf["Tempo Total"] = subdf["Tempo Total"].str.replace(",", ".").str.extract(r"(\d{2}:\d{2}:\d{2})")[0]
            tempos_validos = pd.to_timedelta(subdf["Tempo Total"], errors='coerce')

            tempo_total = tempos_validos.dropna().sum()
            segundos = int(tempo_total.total_seconds())
            tempo_formatado = f"{segundos // 3600:02} H:{(segundos % 3600) // 60:02} M:{segundos % 60:02} S"

            trabalho = {
                "Grupo": grupo_nome,
                "Proposta": subdf.iloc[0]["Proposta"],
                "Espessura": subdf.iloc[0]["Espessura"],
                "Material": subdf.iloc[0]["Material"],
                "Qtd Total": pd.to_numeric(subdf["Qtd Chapas"], errors='coerce').fillna(0).astype(int).sum(),
                "Tempo Total": tempo_formatado,
                "Detalhes": subdf.to_dict(orient="records")
            }

            extras = infos_adicionais.get(grupo_nome, {})
            if extras.get("Data Prevista"):
                trabalho["Data Prevista"] = extras["Data Prevista"]
            if extras.get("Processos"):
                trabalho["Processos"] = extras["Processos"]

            trabalhos_categoria.append(trabalho)

        trabalhos[categoria] = trabalhos_categoria

    return trabalhos