import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password=""
    )
    
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS payroll_db")
    cursor.execute("USE payroll_db")
    
    print("DB Created/Connected Successfully!")
    
except Exception as e:
    print("Error:", e)