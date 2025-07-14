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
            tempo_total TEXT
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
        INSERT INTO fila_maquinas (maquina, proposta, cnc, material, espessura, quantidade, tempo_total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (maquina, trabalho["Proposta"], trabalho["CNC"], trabalho["Material"],
          trabalho["Espessura"], trabalho["Quantidade"], trabalho["Tempo Total"]))
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