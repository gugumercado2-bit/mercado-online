# app.py
from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

DB_FILE = "database.db"

# ================= Banco =================
def conectar():
    return sqlite3.connect(DB_FILE)

def criar_tabelas():
    with conectar() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            senha TEXT,
            nivel TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            codigo TEXT PRIMARY KEY,
            nome TEXT,
            preco REAL,
            estoque INTEGER,
            vendidos INTEGER DEFAULT 0
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            total REAL,
            pagamento TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS fiado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            produto TEXT,
            quantidade INTEGER,
            subtotal REAL,
            data TEXT
        )""")
        conn.commit()

criar_tabelas()

# ================= Rotas Frontend =================
@app.route("/")
def home():
    return render_template("index.html")

# ================= Produtos =================
@app.route("/produtos", methods=["GET", "POST"])
def produtos():
    if request.method == "GET":
        with conectar() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM produtos")
            produtos = c.fetchall()
            return jsonify([{"codigo": p[0], "nome": p[1], "preco": p[2], "estoque": p[3], "vendidos": p[4]} for p in produtos])
    else:
        data = request.json
        codigo = data.get("codigo")
        nome = data.get("nome")
        preco = data.get("preco")
        estoque = data.get("estoque")
        try:
            with conectar() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO produtos (codigo, nome, preco, estoque) VALUES (?, ?, ?, ?)",
                          (codigo, nome, preco, estoque))
                conn.commit()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

# ================= Registrar Venda =================
@app.route("/vendas", methods=["POST"])
def registrar_venda():
    data = request.json
    total = data.get("total")
    pagamento = data.get("pagamento")
    itens = data.get("itens")
    cliente = data.get("cliente")  # Para fiado

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with conectar() as conn:
        c = conn.cursor()
        # registrar venda normal
        c.execute("INSERT INTO vendas (data, total, pagamento) VALUES (?, ?, ?)",
                  (now, total, pagamento))
        # atualizar estoque e vendidos
        for item in itens:
            c.execute("SELECT estoque, vendidos FROM produtos WHERE codigo=?", (item["codigo"],))
            estoque, vendidos = c.fetchone()
            novo_estoque = estoque - item["quantidade"]
            novos_vendidos = vendidos + item["quantidade"]
            c.execute("UPDATE produtos SET estoque=?, vendidos=? WHERE codigo=?",
                      (novo_estoque, novos_vendidos, item["codigo"]))
            # se fiado
            if pagamento == "fiado":
                c.execute("INSERT INTO fiado (cliente, produto, quantidade, subtotal, data) VALUES (?, ?, ?, ?, ?)",
                          (cliente, item["nome"], item["quantidade"], item["subtotal"], now))
        conn.commit()
    return jsonify({"success": True})

# ================= Fiado =================
@app.route("/fiado/<cliente>", methods=["GET"])
def fiado_cliente(cliente):
    with conectar() as conn:
        c = conn.cursor()
        c.execute("SELECT produto, quantidade, subtotal, data FROM fiado WHERE cliente=?", (cliente,))
        dados = c.fetchall()
        total = sum(d[2] for d in dados)
        return jsonify({"itens": [{"produto": d[0], "quantidade": d[1], "subtotal": d[2], "data": d[3]} for d in dados],
                        "total": total})

# ================= Fechamento de Caixa =================
@app.route("/fechar_caixa", methods=["GET"])
def fechar_caixa():
    with conectar() as conn:
        c = conn.cursor()
        hoje = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT total, data FROM vendas WHERE data LIKE ?", (hoje+"%",))
        vendas = c.fetchall()
        total = sum(v[0] for v in vendas)
        return jsonify({"vendas": [{"total": v[0], "data": v[1]} for v in vendas],
                        "lucro_total": total})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)