def carregar_trabalhos(pasta="autorizados"):
    from pathlib import Path
    import pandas as pd

    registros = []
    infos_adicionais = {}

    pasta_path = Path(pasta)
    if not pasta_path.exists():
        return []

    arquivos_txt = list(pasta_path.glob("*.txt"))
    if not arquivos_txt:
        return []

    for txt in arquivos_txt:
        partes = txt.stem.split("-")
        if len(partes) != 3:
            continue

        chave_grupo = "-".join(partes)
        with open(txt, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()

        # Separa blocos
        blocos = conteudo.split("\n\n")

        for bloco in blocos:
            if "===== INFORMAÇÕES ADICIONAIS =====" in bloco:
                for linha in bloco.splitlines():
                    if linha.startswith("Data prevista:"):
                        infos_adicionais.setdefault(chave_grupo, {})["Data Prevista"] = linha.split(":", 1)[1].strip()
                    elif linha.startswith("Processos:"):
                        infos_adicionais.setdefault(chave_grupo, {})["Processos"] = linha.split(":", 1)[1].strip()
                # ⚠️ pula esse bloco para não processar como CNC
                continue

            # IGNORA blocos que não contêm CNC
            if not bloco.strip().startswith("Programador:"):
                continue

            dados = {}
            for linha in bloco.strip().splitlines():
                if ":" in linha:
                    k, v = linha.split(":", 1)
                    dados[k.strip()] = v.strip()

            if dados.get("CNC"):  # só adiciona se tiver CNC válido
                registros.append({
                    "Grupo": chave_grupo,
                    "Proposta": partes[0],
                    "Espessura": float(partes[1]) / 100,
                    "Material": partes[2],
                    "CNC": dados.get("CNC", ""),
                    "Programador": dados.get("Programador", ""),
                    "Qtd Chapas": dados.get("Qtd Chapas", "1"),
                    "Tempo Total": dados.get("Tempo Total", ""),
                    "Caminho": dados.get("Caminho", "")
                })

    df = pd.DataFrame(registros)
    if df.empty:
        return []

    trabalhos = []

    for grupo_nome, subdf in df.groupby("Grupo"):
        subdf["Tempo Total"] = subdf["Tempo Total"].str.replace(r"\.\d+$", "", regex=True)
        tempos_validos = pd.to_timedelta(subdf["Tempo Total"], errors='coerce')
        tempo_total = tempos_validos.dropna().sum()
        segundos = int(tempo_total.total_seconds())
        tempo_formatado = f"{segundos // 3600:02} H:{(segundos % 3600) // 60:02} M:{segundos % 60:02} S"

        trabalho = {
            "Grupo": grupo_nome,
            "Proposta": subdf.iloc[0]["Proposta"],
            "Espessura": subdf.iloc[0]["Espessura"],
            "Material": subdf.iloc[0]["Material"],
            "Qtd Total": subdf["Qtd Chapas"].astype(int).sum(),
            "Tempo Total": tempo_formatado,
            "Detalhes": subdf.to_dict(orient="records")
        }

        # Adiciona as informações extras, se existirem
        extras = infos_adicionais.get(grupo_nome, {})
        if extras.get("Data Prevista"):
            trabalho["Data Prevista"] = extras["Data Prevista"]
        if extras.get("Processos"):
            trabalho["Processos"] = extras["Processos"]

        trabalhos.append(trabalho)

    return trabalhos
