# library_cli.py
import mysql.connector
from tabulate import tabulate
from datetime import date, timedelta
from config import DB_CONFIG

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def list_books():
    q = """
    SELECT b.book_id, b.title,
           COUNT(c.copy_id) AS total_copies,
           SUM(c.status='available') AS available_copies
    FROM books b
    LEFT JOIN book_copies c ON b.book_id=c.book_id
    GROUP BY b.book_id, b.title
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q)
        rows = cur.fetchall()
    print(tabulate(rows, headers=['ID','Title','Total','Available']))

def add_member():
    name = input("Name: ").strip()
    email = input("Email: ").strip()
    phone = input("Phone: ").strip()
    addr = input("Address: ").strip()
    q = "INSERT INTO members (name,email,phone,address) VALUES (%s,%s,%s,%s)"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, (name,email,phone,addr))
        conn.commit()
    print("Member added, id:", cur.lastrowid)

def add_book():
    title = input("Title: ").strip()
    author = input("Author: ").strip()
    publisher = input("Publisher: ").strip()
    year = input("Year (YYYY): ").strip() or None
    category = input("Category: ").strip()
    copies = int(input("Number of copies: ") or 1)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO books (title,author,publisher,year,category) VALUES (%s,%s,%s,%s,%s)",
                    (title,author,publisher,year,category))
        book_id = cur.lastrowid
        for _ in range(copies):
            cur.execute("INSERT INTO book_copies (book_id) VALUES (%s)", (book_id,))
        conn.commit()
    print(f"Added book id {book_id} with {copies} copies.")

def issue_book():
    copy_id = int(input("Copy ID to issue: "))
    member_id = int(input("Member ID: "))
    loan_days = int(input("Loan days (default 14): ") or 14)
    with get_conn() as conn:
        cur = conn.cursor()
        # check availability
        cur.execute("SELECT status FROM book_copies WHERE copy_id=%s FOR UPDATE", (copy_id,))
        row = cur.fetchone()
        if not row:
            print("Copy not found.")
            return
        if row[0] != 'available':
            print("Copy not available.")
            return
        cur.execute("INSERT INTO issue_records (copy_id,member_id,issue_date,due_date) VALUES (%s,%s,%s,%s)",
                    (copy_id, member_id, date.today(), date.today()+timedelta(days=loan_days)))
        cur.execute("UPDATE book_copies SET status='issued' WHERE copy_id=%s", (copy_id,))
        conn.commit()
        print("Issued successfully, issue_id:", cur.lastrowid)

def return_book():
    copy_id = int(input("Copy ID to return: "))
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT issue_id,due_date FROM issue_records WHERE copy_id=%s AND return_date IS NULL FOR UPDATE", (copy_id,))
        row = cur.fetchone()
        if not row:
            print("No active issue for that copy.")
            return
        issue_id, due_date = row
        today = date.today()
        fine = max((today - due_date).days, 0)
        cur.execute("UPDATE issue_records SET return_date=%s WHERE issue_id=%s", (today,issue_id))
        cur.execute("UPDATE book_copies SET status='available' WHERE copy_id=%s", (copy_id,))
        conn.commit()
        print(f"Returned. Fine: {fine} (per day charged externally)")

def overdue_report():
    q = """
    SELECT ir.issue_id, m.name, b.title, ir.due_date, DATEDIFF(CURDATE(), ir.due_date) AS days_overdue
    FROM issue_records ir
    JOIN book_copies bc ON ir.copy_id = bc.copy_id
    JOIN books b ON bc.book_id = b.book_id
    JOIN members m ON ir.member_id = m.member_id
    WHERE ir.return_date IS NULL AND ir.due_date < CURDATE()
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q)
        rows = cur.fetchall()
    print(tabulate(rows, headers=['Issue ID','Member','Title','Due Date','Days Overdue']))

def menu():
    while True:
        print("\n1 List Books  2 Add Member  3 Add Book  4 Issue  5 Return  6 Overdue  0 Exit")
        choice = input("Choice: ").strip()
        if choice=='1': list_books()
        elif choice=='2': add_member()
        elif choice=='3': add_book()
        elif choice=='4': issue_book()
        elif choice=='5': return_book()
        elif choice=='6': overdue_report()
        elif choice=='0': break
        else: print("Invalid")

if __name__ == '__main__':
    menu()
