# utils/db.py

import sqlite3
from pathlib import Path

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
        CREATE TABLE IF NOT EXISTS trabalhos_enviados (
            grupo TEXT PRIMARY KEY,
            proposta TEXT,
            cnc TEXT,
            material TEXT,
            espessura REAL,
            quantidade INTEGER,
            tempo_total TEXT,
            programador TEXT,
            data_prevista TEXT,
            processos TEXT
        )
    """)
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
    cursor.execute("SELECT rowid, quantidade FROM corte_atual WHERE maquina = ?", (maquina,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return

    rowid, quantidade = row

    if quantidade > 1:
        cursor.execute("UPDATE corte_atual SET quantidade = ? WHERE rowid = ?", (quantidade - 1, rowid))
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


def excluir_pendente(grupo: str, pasta="autorizados"):
    caminho = Path(pasta) / f"{grupo}.txt"
    if caminho.exists():
        caminho.unlink()


def retornar_para_pendentes(maquina: str, pasta="autorizados"):
    from datetime import datetime

    corte = obter_corte_atual(maquina)
    if not corte:
        return

    _, proposta, cnc, material, espessura, quantidade, tempo_total = corte
    grupo_nome = f"{proposta}-{int(espessura * 100):04}-{material}"

    # Busca dados originais do trabalho enviado
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT programador, data_prevista, processos
        FROM trabalhos_enviados
        WHERE grupo = ?
    """, (grupo_nome,))
    resultado = cursor.fetchone()
    conn.close()

    programador = resultado[0] if resultado and resultado[0] else "DESCONHECIDO"
    data_prevista = resultado[1] if resultado and resultado[1] else str(datetime.today().date())
    processos = resultado[2] if resultado and resultado[2] else "Corte Retornado"

    conteudo = f"""Programador: {programador}
CNC: {cnc}
Qtd Chapas: {quantidade}
Tempo Total: {tempo_total}
Caminho: CNC/{cnc}.pdf

===== INFORMAÇÕES ADICIONAIS =====
Data prevista: {data_prevista}
Processos: {processos}
"""

    caminho = Path(pasta) / f"{grupo_nome}.txt"
    modo_arquivo = "a" if caminho.exists() else "w"

    with open(caminho, modo_arquivo, encoding="utf-8") as f:
        if caminho.exists():
            f.write("\n\n")  # separa o novo bloco do anterior
        f.write(conteudo)
    excluir_do_corte(maquina)

def retornar_item_da_fila_para_pendentes(id_trabalho: int, pasta="autorizados"):
    from datetime import datetime

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

    # Buscar dados salvos no registro
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

    conteudo = f"""Programador: {programador}
CNC: {cnc}
Qtd Chapas: {quantidade}
Tempo Total: {tempo_total}
Caminho: CNC/{cnc}.pdf

===== INFORMAÇÕES ADICIONAIS =====
Data prevista: {data_prevista}
Processos: {processos}
"""

    caminho = Path(pasta) / f"{grupo}.txt"
    modo_arquivo = "a" if caminho.exists() else "w"

    with open(caminho, modo_arquivo, encoding="utf-8") as f:
        if caminho.exists():
            f.write("\n\n")  # separa o novo bloco do anterior
        f.write(conteudo)

    excluir_da_fila("", id_trabalho)  # "" já é ignorado no SQL
