def carregar_trabalhos(pasta=r"C:\Users\Microns\Desktop\Macros\ERP\Programas_Prontos"):
    from pathlib import Path
    import pandas as pd
    registros = []

    for txt in Path(pasta).glob("*.txt"):
        partes = txt.stem.split("-")
        if len(partes) >= 4:
            chave_grupo = "-".join(partes[:3])
            cnc = partes[3]
            with open(txt, "r", encoding="utf-8") as f:
                linhas = f.read().splitlines()
                dados = {linha.split(":", 1)[0].strip(): linha.split(":", 1)[1].strip() for linha in linhas if ":" in linha}

            registros.append({
                "Grupo": chave_grupo,
                "Proposta": partes[0],
                "Espessura": float(partes[1]) / 100,
                "Material": partes[2],
                "CNC": cnc,
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
