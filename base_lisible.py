import sqlite3

conn = sqlite3.connect("auth/users.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

for table in tables:
    table_name = table[0]
    print(f"\n--- Contenu de la table  {table_name} ---")
    
    cursor.execute(f"PRAGMA table_info({table_name});")
    colonnes = [col[1] for col in cursor.fetchall()]
    print("Colonnes:", colonnes)
    
    cursor.execute(f"SELECT * FROM {table_name};")
    lignes = cursor.fetchall()
    
    for ligne in lignes:
        print(ligne)

conn.close()