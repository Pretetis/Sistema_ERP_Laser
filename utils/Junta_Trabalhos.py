def carregar_trabalhos(pasta="autorizados"):
    from pathlib import Path
    import pandas as pd

    registros = []

    for txt in Path(pasta).glob("*.txt"):
        partes = txt.stem.split("-")
        if len(partes) == 3:
            chave_grupo = "-".join(partes)
            with open(txt, "r", encoding="utf-8") as f:
                blocos = f.read().strip().split("\n\n")  # divide por blocos de CNC

            for bloco in blocos:
                dados = {}
                for linha in bloco.strip().splitlines():
                    if ":" in linha:
                        k, v = linha.split(":", 1)
                        dados[k.strip()] = v.strip()

                if dados:
                    registros.append({
                        "Grupo": chave_grupo,
                        "Proposta": partes[0],
                        "Espessura": float(partes[1]) / 100,
                        "Material": partes[2],
                        "CNC": dados.get("CNC", ""),
                        "Programador": dados.get("Programador", ""),
                        "Qtd Chapas": dados.get("Qtd Chapas", "1"),
                        "Tempo Total": dados.get("Tempo Total", ""),
                        "Caminho PDF": dados.get("Caminho", "")
                    })

    df = pd.DataFrame(registros)
    trabalhos = []

    for grupo_nome, subdf in df.groupby("Grupo"):
        subdf["Tempo Total"] = subdf["Tempo Total"].str.replace(r"\.\d+$", "", regex=True)
        tempos_validos = pd.to_timedelta(subdf["Tempo Total"], errors='coerce')
        tempo_total = tempos_validos.dropna().sum()
        segundos = int(tempo_total.total_seconds())
        tempo_formatado = f"{segundos // 3600:02} H:{(segundos % 3600) // 60:02} M:{segundos % 60:02} S"

        trabalhos.append({
            "Grupo": grupo_nome,
            "Proposta": subdf.iloc[0]["Proposta"],
            "Espessura": subdf.iloc[0]["Espessura"],
            "Material": subdf.iloc[0]["Material"],
            "Qtd Total": subdf["Qtd Chapas"].astype(int).sum(),
            "Tempo Total": tempo_formatado,
            "Detalhes": subdf.to_dict(orient="records")
        })

    return trabalhos