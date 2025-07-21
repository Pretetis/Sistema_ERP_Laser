import sqlite3
from pathlib import Path
from datetime import datetime

from utils.supabase import baixar_txt_conteudo, upload_txt_to_supabase 

DB_PATH = Path("estado_maquinas.db")

def criar_banco():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fila_maquinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maquina TEXT,
            proposta TEXT,
            cnc TEXT,
            material TEXT,
            espessura REAL,
            quantidade INTEGER,
            tempo_total TEXT,
            caminho TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corte_atual (
            maquina TEXT PRIMARY KEY,
            proposta TEXT,
            cnc TEXT,
            material TEXT,
            espessura REAL,
            quantidade INTEGER,
            tempo_total TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trabalhos_enviados (
            grupo TEXT,
            proposta TEXT,
            cnc TEXT,
            material TEXT,
            espessura REAL,
            quantidade INTEGER,
            tempo_total TEXT,
            programador TEXT,
            data_prevista TEXT,
            processos TEXT,
            PRIMARY KEY (grupo, cnc)
        )
    """)

    conn.commit()
    conn.close()


def adicionar_na_fila(maquina, trabalho):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO fila_maquinas (maquina, proposta, cnc, material, espessura, quantidade, tempo_total, caminho)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (maquina, trabalho["Proposta"], trabalho["CNC"], trabalho["Material"],
          trabalho["Espessura"], trabalho["Quantidade"], trabalho["Tempo Total"], trabalho["Caminho"]))
    conn.commit()
    conn.close()


def registrar_trabalho_enviado(grupo, proposta, cnc, material, espessura,
                               quantidade, tempo_total, programador,
                               data_prevista=None, processos=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO trabalhos_enviados
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        grupo, proposta, cnc, material, espessura, quantidade,
        tempo_total, programador, data_prevista, processos
    ))
    conn.commit()
    conn.close()


def obter_fila(maquina):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fila_maquinas WHERE maquina = ?", (maquina,))
    resultados = cursor.fetchall()
    conn.close()
    return resultados


def iniciar_corte(maquina, id_fila):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fila_maquinas WHERE id = ?", (id_fila,))
    item = cursor.fetchone()

    if item:
        cursor.execute("DELETE FROM fila_maquinas WHERE id = ?", (id_fila,))
        cursor.execute("""
            INSERT OR REPLACE INTO corte_atual
            (maquina, proposta, cnc, material, espessura, quantidade, tempo_total)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, item[1:])  # ignora o ID

    conn.commit()
    conn.close()


def finalizar_corte(maquina):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT quantidade FROM corte_atual WHERE maquina = ?", (maquina,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return

    quantidade = row[0]

    if quantidade > 1:
        cursor.execute("UPDATE corte_atual SET quantidade = ? WHERE maquina = ?", (quantidade - 1, maquina))
    else:
        cursor.execute("DELETE FROM corte_atual WHERE maquina = ?", (maquina,))

    conn.commit()
    conn.close()


def obter_corte_atual(maquina):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM corte_atual WHERE maquina = ?", (maquina,))
    corte = cursor.fetchone()
    conn.close()
    return corte


def atualizar_quantidade(id_trabalho: int, nova_quantidade: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE corte_atual
        SET quantidade = ?
        WHERE rowid = ?
    """, (nova_quantidade, id_trabalho))
    conn.commit()
    conn.close()


def excluir_da_fila(maquina: str, id_trabalho: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fila_maquinas WHERE maquina = ? AND id = ?", (maquina, id_trabalho))
    conn.commit()
    conn.close()


def excluir_do_corte(maquina: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM corte_atual WHERE maquina = ?", (maquina,))
    conn.commit()
    conn.close()


def excluir_pendente(grupo: str):
    # Nenhuma ação necessária, pois o TXT está apenas no Cloudinary
    pass


def retornar_para_pendentes(maquina: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    corte = obter_corte_atual(maquina)
    if not corte:
        return

    _, proposta, cnc, material, espessura, quantidade, tempo_total = corte
    grupo = f"{proposta}-{int(espessura * 100):04}-{material}"

    cursor.execute("""
        SELECT programador, data_prevista, processos
        FROM trabalhos_enviados
        WHERE grupo = ? AND cnc = ?
    """, (grupo, cnc))
    resultado = cursor.fetchone()
    conn.close()

    programador = resultado[0] if resultado else "DESCONHECIDO"
    data_prevista = resultado[1] if resultado else str(datetime.today().date())
    processos = resultado[2] if resultado else "Corte Retornado"

    conteudo = f"""Programador: {programador}
CNC: {cnc}
Qtd Chapas: {quantidade}
Tempo Total: {tempo_total}
Caminho: CNC/{cnc}.pdf

===== INFORMAÇÕES ADICIONAIS =====
Data prevista: {data_prevista}
Processos: {processos}
"""

    nome_arquivo = f"trabalhos_pendentes-{grupo}-{cnc}.txt"
    upload_txt_to_supabase(nome_arquivo, conteudo)  # ✅ Substituído

    excluir_do_corte(maquina)


def retornar_item_da_fila_para_pendentes(id_trabalho: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, maquina, proposta, cnc, material, espessura,
               quantidade, tempo_total
        FROM fila_maquinas
        WHERE id = ?
    """, (id_trabalho,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return

    _, _, proposta, cnc, material, espessura, quantidade, tempo_total = row
    grupo = f"{proposta}-{int(espessura * 100):04}-{material}"

    # Buscar dados extras do programador, etc.
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT programador, data_prevista, processos
        FROM trabalhos_enviados
        WHERE grupo = ? AND cnc = ?
    """, (grupo, cnc))
    res = cursor.fetchone()
    conn.close()

    programador = res[0] if res else "DESCONHECIDO"
    data_prevista = res[1] if res else str(datetime.today().date())
    processos = res[2] if res else "Corte Retornado"

    # Baixar conteúdo existente do Supabase (se existir)
    try:
        conteudo_atual = baixar_txt_conteudo(f"{grupo}.txt", pasta="trabalhos_pendentes")
    except Exception:
        conteudo_atual = ""

    # Adicionar novo CNC ao conteúdo
    novo_bloco = f"""Programador: {programador}
CNC: {cnc}
Qtd Chapas: {quantidade}
Tempo Total: {tempo_total}
Caminho: CNC/{cnc}.pdf
"""

    # Reconstruir conteúdo: colocar novo bloco acima das infos adicionais (se houver)
    if "===== INFORMAÇÕES ADICIONAIS =====" in conteudo_atual:
        partes = conteudo_atual.split("===== INFORMAÇÕES ADICIONAIS =====")
        principal = partes[0].strip()
        adicionais = partes[1].strip()
        novo_conteudo = f"{principal}\n\n{novo_bloco}\n\n===== INFORMAÇÕES ADICIONAIS =====\n{adicionais}"
    else:
        novo_conteudo = f"{conteudo_atual.strip()}\n\n{novo_bloco}".strip()

        # Adiciona informações adicionais se forem novas
        novo_conteudo += f"""

===== INFORMAÇÕES ADICIONAIS =====
Data prevista: {data_prevista}
Processos: {processos}
"""

    # Enviar novo arquivo
    upload_txt_to_supabase(f"{grupo}.txt", novo_conteudo, pasta="trabalhos_pendentes")

    # Remove da fila
    excluir_da_fila("", id_trabalho)