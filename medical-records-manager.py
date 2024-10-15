import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from tkinterdnd2 import DND_FILES, TkinterDnD
import sqlite3
from datetime import datetime
import csv
import base64

# Import the AES functions
from aes_encryption import generate_key, encrypt, decrypt

class LoginWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Login")
        self.geometry("300x150")
        self.configure(bg="#f0f0f0")

        ttk.Label(self, text="Username:").pack(pady=5)
        self.username_entry = ttk.Entry(self)
        self.username_entry.pack(pady=5)

        ttk.Label(self, text="Password:").pack(pady=5)
        self.password_entry = ttk.Entry(self, show="*")
        self.password_entry.pack(pady=5)

        ttk.Button(self, text="Login", command=self.login).pack(pady=10)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if self.parent.verify_credentials(username, password):
            self.parent.current_user = username
            self.destroy()
            self.parent.deiconify()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")

class MedicalRecordsApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.title("Medical Records Manager")
        self.geometry("800x600")
        self.configure(bg="#f0f0f0")
        self.withdraw()  # Hide the main window initially

        self.style = ttk.Style(self)
        self.style.theme_create("medical_theme", parent="alt", settings={
            "TFrame": {"configure": {"background": "#f0f0f0"}},
            "TButton": {"configure": {"padding": [10, 5], "background": "#4CAF50", "foreground": "white"}},
            "TLabel": {"configure": {"background": "#f0f0f0", "foreground": "black"}},
            "TEntry": {"configure": {"insertbackground": "black"}},
        })
        self.style.theme_use("medical_theme")

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(pady=10, padx=10, expand=True, fill="both")

        self.create_database()
        self.create_widgets()

        self.current_user = None
        self.login_window = LoginWindow(self)

    def create_database(self):
        conn = sqlite3.connect('medical_records.db')
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         username TEXT UNIQUE,
         password TEXT)
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS records
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         patient_name TEXT,
         date_added TEXT,
         file_path TEXT,
         encrypted_data BLOB,
         aes_key BLOB)
        ''')
        conn.commit()
        conn.close()

    def create_widgets(self):
        # Patient name entry
        ttk.Label(self.main_frame, text="Patient Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.patient_name = tk.StringVar()
        ttk.Entry(self.main_frame, textvariable=self.patient_name, width=40).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # File selection
        ttk.Label(self.main_frame, text="Select File:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.file_path = tk.StringVar()
        ttk.Entry(self.main_frame, textvariable=self.file_path, width=40).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self.main_frame, text="Browse", command=self.browse_file).grid(row=1, column=2, padx=5, pady=5)

        # Add record button
        ttk.Button(self.main_frame, text="Add Record", command=self.add_record).grid(row=2, column=1, padx=5, pady=10)

        # Records list
        self.records_tree = ttk.Treeview(self.main_frame, columns=("ID", "Patient", "Date", "File"), show="headings")
        self.records_tree.heading("ID", text="ID")
        self.records_tree.heading("Patient", text="Patient Name")
        self.records_tree.heading("Date", text="Date Added")
        self.records_tree.heading("File", text="File Name")
        self.records_tree.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

        # Scrollbar for the treeview
        scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.records_tree.yview)
        scrollbar.grid(row=4, column=3, sticky="ns")
        self.records_tree.configure(yscrollcommand=scrollbar.set)

        # Decryption frame
        decrypt_frame = ttk.Frame(self.main_frame)
        decrypt_frame.grid(row=5, column=0, columnspan=3, padx=5, pady=10, sticky="ew")

        ttk.Label(decrypt_frame, text="Select Record ID to Decrypt:").pack(side=tk.LEFT, padx=5)
        self.decrypt_id_var = tk.StringVar()
        self.decrypt_id_entry = ttk.Entry(decrypt_frame, textvariable=self.decrypt_id_var, width=10)
        self.decrypt_id_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(decrypt_frame, text="Decrypt Record", command=self.decrypt_record).pack(side=tk.LEFT, padx=5)

        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(4, weight=1)

    def verify_credentials(self, username, password):
        conn = sqlite3.connect('medical_records.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()
        return user is not None

    def browse_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.file_path.set(filename)

    def add_record(self):
        patient_name = self.patient_name.get()
        file_path = self.file_path.get()

        if not patient_name or not file_path:
            messagebox.showerror("Error", "Please enter patient name and select a file.")
            return

        date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        key = generate_key()

        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                encrypted_data = encrypt(file_content, key)

            conn = sqlite3.connect('medical_records.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO records (patient_name, date_added, file_path, encrypted_data, aes_key) VALUES (?, ?, ?, ?, ?)",
                           (patient_name, date_added, os.path.basename(file_path), sqlite3.Binary(encrypted_data), sqlite3.Binary(key)))
            conn.commit()
            messagebox.showinfo("Success", "Record added successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            conn.close()

        self.load_records()
        self.patient_name.set("")
        self.file_path.set("")

    def load_records(self):
        self.records_tree.delete(*self.records_tree.get_children())
        conn = sqlite3.connect('medical_records.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, patient_name, date_added, file_path FROM records ORDER BY date_added DESC")
        for row in cursor.fetchall():
            self.records_tree.insert("", "end", values=row)
        conn.close()

    def decrypt_record(self):
        record_id = self.decrypt_id_var.get()
        if not record_id:
            messagebox.showerror("Error", "Please enter a Record ID to decrypt.")
            return

        conn = sqlite3.connect('medical_records.db')
        cursor = conn.cursor()
        cursor.execute("SELECT encrypted_data, aes_key, file_path FROM records WHERE id=?", (record_id,))
        record = cursor.fetchone()
        conn.close()

        if record:
            encrypted_data, aes_key, original_filename = record
            decrypted_data = decrypt(encrypted_data, aes_key)

            save_path = filedialog.asksaveasfilename(defaultextension="", initialfile=original_filename)
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(decrypted_data)
                messagebox.showinfo("Success", f"File decrypted and saved as {save_path}")
        else:
            messagebox.showerror("Error", "Record not found.")

if __name__ == "__main__":
    app = MedicalRecordsApp()
    app.mainloop()
