from flask import Flask, render_template, request, redirect, url_for, Response
import sqlite3
from datetime import datetime
import csv
import io

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('toko_kelontong.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_barang TEXT UNIQUE NOT NULL,
            stok INTEGER NOT NULL,
            harga_jual INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_barang TEXT NOT NULL,
            qty INTEGER NOT NULL,
            total_harga INTEGER NOT NULL,
            tanggal TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    conn = sqlite3.connect('toko_kelontong.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    
    cursor.execute('SELECT * FROM products WHERE stok <= 5')
    low_stock = cursor.fetchall()
    
    cursor.execute('SELECT SUM(total_harga) AS total_pendapatan FROM transactions')
    pendapatan_row = cursor.fetchone()
    total_pendapatan = pendapatan_row['total_pendapatan'] if pendapatan_row['total_pendapatan'] else 0
    
    cursor.execute('SELECT * FROM transactions ORDER BY id DESC')
    transactions = cursor.fetchall()
    
    conn.close()
    return render_template('index.html', products=products, low_stock=low_stock, total_pendapatan=total_pendapatan, transactions=transactions)

# Logika Tambah Produk / Restok Otomatis Jika Nama Sama
@app.route('/add_product', methods=['POST'])
def add_product():
    nama = request.form['nama_barang'].strip().lower()
    stok_tambah = int(request.form['stok'])
    harga_jual = int(request.form['harga_jual'])
    
    conn = sqlite3.connect('toko_kelontong.db')
    cursor = conn.cursor()
    
    # Cek apakah barang dengan nama yang sama sudah ada
    cursor.execute('SELECT * FROM products WHERE LOWER(nama_barang) = ?', (nama,))
    existing_product = cursor.fetchone()
    
    if existing_product:
        # Jika sudah ada, update stoknya (ditambahkan dengan stok baru) dan update harga
        new_total_stok = existing_product[2] + stok_tambah
        cursor.execute('UPDATE products SET stok = ?, harga_jual = ? WHERE LOWER(nama_barang) = ?', 
                       (new_total_stok, harga_jual, nama))
    else:
        # Jika belum ada, masukkan sebagai produk baru
        cursor.execute('INSERT INTO products (nama_barang, stok, harga_jual) VALUES (?, ?, ?)',
                       (nama, stok_tambah, harga_jual))
        
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# Route khusus untuk tombol Restok cepat di tabel
@app.route('/restock/<int:product_id>', methods=['POST'])
def restock(product_id):
    tambah_stok = int(request.form['tambah_stok'])
    
    conn = sqlite3.connect('toko_kelontong.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE products SET stok = stok + ? WHERE id = ?', (tambah_stok, product_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/checkout', methods=['POST'])
def checkout():
    product_id = request.form['product_id']
    qty = int(request.form['qty'])
    
    conn = sqlite3.connect('toko_kelontong.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if product and product['stok'] >= qty:
        total_harga = product['harga_jual'] * qty
        new_stok = product['stok'] - qty
        nama_barang = product['nama_barang']
        tanggal = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        cursor.execute('UPDATE products SET stok = ? WHERE id = ?', (new_stok, product_id))
        cursor.execute('INSERT INTO transactions (nama_barang, qty, total_harga, tanggal) VALUES (?, ?, ?, ?)',
                       (nama_barang, qty, total_harga, tanggal))
        conn.commit()
        
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/export_report')
def export_report():
    conn = sqlite3.connect('toko_kelontong.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, tanggal, nama_barang, qty, total_harga FROM transactions')
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID Transaksi', 'Tanggal & Waktu', 'Nama Barang', 'Jumlah Beli', 'Total Harga (Rp)'])
    for row in rows:
        writer.writerow(row)
        
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=Laporan_Keuangan_Toko.csv"}
    )

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8080)  