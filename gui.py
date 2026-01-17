import os
import binascii
import json
import time
import webbrowser
import difflib
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from ttkthemes import ThemedTk
from hexmap import decode_custom_hex, EXCLUDED_HEX_CODES
from core import (
    open_with_default_app,
    hfs_timestamp_to_datetime,
    parse_allocation_bitmap,
    parse_extents_overflow,
    parse_catalog_btree,
    extract_ascii_strings,
    parse_delete_log,
    parse_mdb,
    split_file_on_marker,
    extract_after_etx_mcw,
    estrai_prima_stesura_hex_da_mcw_bytes,
    converti_mcw_in_odt,
    estrai_testo_da_odt,
    normalizza_rimuovi_righe_vuote,
    normalizza_per_diff,
    estrai_date_catalog,
    ETX_MARKERS,
    type_descriptions,
)


# =============================================================================
#                                START GUI
# =============================================================================

class HFSToolkitGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("eFFe Quadro - Forensic Toolkit")
        root.geometry("1100x750")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(root)
        self.notebook.grid(sticky="nsew")
        self._add_main_menu()

    #==== Build each feature tab ======#

        # File system HFS
        self._build_info_tab()
        self._build_allocation_tab()
        self._build_catalog_tab()
        self._build_mdb_tab()
        self._build_delete_tab()
        self._build_date_tab()

        # Documenti MCW
        self._build_mcw_tab()
        self._build_mcw_compare_tab()
        self._build_split_tab()

        # Strumenti
        self._build_hex_tab()


    def _open_file_from_tag(self, path, *_):
        open_with_default_app(path)

    def _add_main_menu(self):
        THEME_LABELS = {
            "aquativo": "Aquativo (acqua brillante)",
            "adapta": "Adapta (Material Design bianco celeste)",
            "black": "Black (Scuro)",
            "blue": "Blue (Chiaro)",
            "breeze": "Breeze (Grigio e celeste)",
            "clearlooks": "Clearlooks (Morbido)",
            "itft1": "ITFT1 (Classico IT)",
            "kroc": "Kroc (Arancione)",
            "plastik": "Plastik (Pulito KDE‑like)",
            "radiance": "Radiance (Ubuntu Like)",
            "xpnative": "XPnative (Tema classico XP)",
        }

        menubar = tk.Menu(self.root)
        try:
            self.root.iconbitmap("logo.ico")
        except Exception:
            # se non trova l'icona su altri sistemi non esplode tutto
            pass
        self.root.config(menu=menubar)


        # --- Menu Guida ---
        guida_menu = tk.Menu(menubar, tearoff=0)
        guida_menu.add_command(label="Apri Guida Utente", command=self._open_guida_tab)
        menubar.add_cascade(label="📘 Guida", menu=guida_menu)

        # --- Menu Credits ---
        credits_menu = tk.Menu(menubar, tearoff=0)
        credits_menu.add_command(
            label="Informazioni sull'autore",
            command=lambda: messagebox.showinfo(
                "Credits",
                "eFFe Quadro - Forensic Toolkit\n"
                "Sviluppato da Mariangela Giglio\n"
                "Versione: 1.0\n"
                "GitHub: https://github.com/mariangiglio\n"
                "Licenza: uso interno / didattico"
            )
        )
        menubar.add_cascade(label="ℹ️ Credits", menu=credits_menu)

        # --- Menu Temi ---
        theme_menu = tk.Menu(menubar, tearoff=0)
        for t in sorted(THEME_LABELS):
            label = THEME_LABELS[t]
            theme_menu.add_command(label=label, command=lambda theme=t: self.root.set_theme(theme))
        menubar.add_cascade(label="🎨 Temi", menu=theme_menu)



#------------------- File info tab -------------------#
    def _build_info_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Info File")
        ttk.Label(tab, text="🔍 Analisi tipo file", foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        # Selettore file
        path_frame = ttk.Frame(tab)
        path_frame.pack(fill="x", padx=5, pady=5)

        self.info_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.info_path_var, width=80).pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text="Scegli File", command=self._select_info_file).pack(side="left", padx=5)

        # Output area
        self.info_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.info_output.pack(fill="both", expand=True, padx=5, pady=5)

    def _select_info_file(self):
        path = filedialog.askopenfilename(title="Seleziona un file da analizzare")
        if path:
            self.info_path_var.set(path)
            self._analyze_info_file(path)

    def _analyze_info_file(self, path):
        import binascii
        self.info_output.delete("1.0", tk.END)
        try:
            with open(path, "rb") as f:
                data = f.read(64)
        except Exception as e:
            self.info_output.insert(tk.END, f"Errore: {e}")
            return

        name = os.path.basename(path).lower()
        known_files = {
            "catalog": "Catalog B-tree",
            "mdb": "MDB (Master Directory Block)",
            "extents": "Extents Overflow",
            "allocation": "Allocation Bitmap",
            "delete": "Delete Log",
            "desktop db": "File di sistema - Desktop DB",
            "desktop": "File di sistema - Desktop",
            "finder.dat": "File di sistema - Finder.dat",
            ".trash": "File di sistema - Cestino",
        }

        # Check by filename
        for key, label in known_files.items():
            if key in name:
                self.info_output.insert(tk.END, f"📄 Riconosciuto: {label}\n")
                break

        # Check magic bytes
        magic_hex = binascii.hexlify(data).upper()
        markers = {
            b"\xFE\x37\x00\x23": "Word 5.0 (dal 1992)",
            b"\xFE\x37\x00\x1C": "Word 4.0 (dal 1990)",
            b"\xFE\x34\x00\x00": "Word 3.0 (dal 1988)",
            b"\xFE\x32\x00": "Write for Atari ST v1.0 (dal 1985)",
        }

        found = False
        for sig, version in markers.items():
            if data.startswith(sig):
                found = True
                self.info_output.insert(tk.END, f"📝 Documento Word riconosciuto: {version}\n")
                if "5.0" in version:
                    self.info_output.insert(tk.END, "• Ultima versione per CPU 68000\n• Parte di Office 3.0\n• Richiede System 6.0.2, RAM 512kB+\n")
                elif "5.1" in version:
                    self.info_output.insert(tk.END, "• Parte di Office 3.0\n• Supporta spellcheck\n")
                elif "6" in version:
                    self.info_output.insert(tk.END, "• Parte di Office 4.2\n• UI condivisa con Word per Windows\n• Richiede System 7.0, 4 MB RAM\n")
                break

        if not found:
            # Heuristic for textual content
            ascii_chars = sum(c < 128 and chr(c).isprintable() for c in data)
            if ascii_chars / len(data) > 0.6:
                self.info_output.insert(tk.END, "✏️ Probabile file testuale\n")
            else:
                self.info_output.insert(tk.END, "❓ Tipo file non determinato con certezza\n")


    # ---------------- Allocation Tab ------------------
    def _build_allocation_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="HFS - Allocation & Extents")
        ttk.Label(tab, text="💾 Analisi su volume HFS (floppy)", foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="Apri Allocation", command=self._load_allocation_bitmap).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Apri Extents Overflow", command=self._load_extents_overflow).pack(side="left", padx=5)

        self.alloc_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.alloc_output.pack(fill="both", expand=True, padx=5, pady=5)

                # Pulsante Salva Output (in basso a destra)
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill="x", pady=5)

        ttk.Button(
            button_frame,
            text="Salva Output",
            command=lambda: self._save_text_widget(self.alloc_output)
        ).pack(side="right", padx=5)


    def _load_allocation_bitmap(self):
        path = filedialog.askopenfilename(title="Seleziona file Allocation (bitmap)")
        if not path:
            return
        used, free, total = parse_allocation_bitmap(path)
        self.alloc_output.delete("1.0", tk.END)
        self.alloc_output.insert(tk.END, f"Blocchi totali: {total}\nBlocchi utilizzati: {used}\nBlocchi liberi: {free}\n\n")
        self.alloc_output.insert(tk.END, f"📂 File: {os.path.basename(path)} (clic per aprire)\n")
        self.alloc_output.tag_add("alloc_link", "5.0", "5.end")
        self.alloc_output.tag_config("alloc_link", foreground="blue", underline=True)
        self.alloc_output.tag_bind("alloc_link", "<Button-1>", lambda e, p=path: open_with_default_app(p))

    def _load_extents_overflow(self):
        path = filedialog.askopenfilename(title="Seleziona file Extents Overflow")
        if not path:
            return

        try:
            results = parse_extents_overflow(path)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il parsing:\n{e}")
            return

        self.alloc_output.delete("1.0", tk.END)

        # 📂 Link al file
        self.alloc_output.insert(tk.END, f"📂 File: {os.path.basename(path)} (clic per aprire)\n\n")
        self.alloc_output.tag_add("extents_link", "1.0", "1.end")
        self.alloc_output.tag_config("extents_link", foreground="blue", underline=True)
        self.alloc_output.tag_bind("extents_link", "<Button-1>", lambda e, p=path: open_with_default_app(p))

        if not results:
            self.alloc_output.insert(tk.END, "Nessun extent valido trovato.\n")
            return

        # 📦 Scrivi tutti i risultati
        for r in results:
            self.alloc_output.insert(
                tk.END,
                f"CNID: {r['CNID']}  Fork: {r['Fork']}\n"
            )
            for i, (start, count) in enumerate(r['Extents'], 1):
                self.alloc_output.insert(tk.END, f"  Extent {i}: blocco iniziale {start}, lunghezza {count}\n")
            self.alloc_output.insert(tk.END, "-" * 50 + "\n")


    # ---------------- Catalog Tab ---------------------
    def _build_catalog_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="HFS - Catalog")
        ttk.Label(tab, text="📂 Sintesi strutturale di cartella o volume HFS con metadati", foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        ttk.Button(tab, text="Apri Catalog B‑tree", command=self._load_catalog).pack(pady=5, padx=5)

        filter_frame = ttk.Frame(tab)
        filter_frame.pack(fill="x", padx=5, pady=5)

        # --- Filtro per nome e tipo ---
        ttk.Label(filter_frame, text="Cerca per nome:").pack(side="left")
        self.catalog_search_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.catalog_search_var, width=20).pack(side="left", padx=5)

        self.catalog_filter_var = tk.StringVar(value="Tutti")
        ttk.Label(filter_frame, text="Filtra per tipo:").pack(side="left", padx=(10, 2))
        ttk.Combobox(filter_frame, textvariable=self.catalog_filter_var,
                     values=["Tutti", "File", "Cartella", "Thread Cartella", "Thread File"],
                     width=15).pack(side="left")

        # --- Filtro per anno ---
        ttk.Label(filter_frame, text="Anno da:").pack(side="left", padx=(10, 2))
        self.catalog_year_from = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.catalog_year_from, width=6).pack(side="left")

        ttk.Label(filter_frame, text="a:").pack(side="left")
        self.catalog_year_to = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.catalog_year_to, width=6).pack(side="left")

        # --- Campo data da analizzare ---
        ttk.Label(filter_frame, text="Campo data:").pack(side="left", padx=(10, 2))
        self.catalog_date_field = tk.StringVar(value="Creato")
        ttk.Combobox(filter_frame, textvariable=self.catalog_date_field,
                     values=["Creato", "Modificato", "Backup"], width=12).pack(side="left")

        # --- Ordinamento ---
        ttk.Label(filter_frame, text="Ordina per:").pack(side="left", padx=(10, 2))
        self.catalog_sort_field = tk.StringVar(value="Nome")
        ttk.Combobox(filter_frame, textvariable=self.catalog_sort_field,
                     values=["Nome", "Tipo", "Data"], width=10).pack(side="left")

        self.catalog_sort_desc = False  # booleano invece di BooleanVar
        self._sort_dir_button = ttk.Button(filter_frame, text="↑ crescente", command=self._toggle_sort_dir)
        self._sort_dir_button.pack(side="left", padx=5)

        # --- Bottone filtro ---
        ttk.Button(filter_frame, text="Applica filtro", command=self._apply_catalog_filters).pack(side="left", padx=10)

        # 1. Area di testo per risultati
        self.catalog_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.catalog_output.pack(fill="both", expand=True, padx=5, pady=5)

        # 2. Pulsante Salva
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill="x", pady=5)

        ttk.Button(button_frame, text="Salva Output Filtrato", command=self._save_catalog_filtered).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Salva Catalog Completo", command=self._save_catalog_full).pack(side="right", padx=5)



    def _toggle_sort_dir(self):
        self.catalog_sort_desc = not self.catalog_sort_desc
        new_text = "↓ decrescente" if self.catalog_sort_desc else "↑ crescente"
        self._sort_dir_button.config(text=new_text)
        self._apply_catalog_filters()


    def _load_catalog(self):
        path = filedialog.askopenfilename(title="Seleziona file Catalog", filetypes=[("Tutti i file", "*.*")])
        if not path:
            return
        try:
            df = parse_catalog_btree(path)
            self._catalog_results = df
            self._catalog_filtered = df.copy()
            self._catalog_current_path = path

            self.catalog_output.delete("1.0", tk.END)
            self.catalog_output.insert(tk.END, f"📂 File: {os.path.basename(path)} (clic per aprire)\n\n")
            self.catalog_output.tag_add("catalog_link", "1.0", "1.end")
            self.catalog_output.tag_config("catalog_link", foreground="blue", underline=True)
            self.catalog_output.tag_bind("catalog_link", "<Button-1>", lambda e, p=path: open_with_default_app(p))

            self._show_catalog(df)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il parsing:\n{e}")



    def _apply_catalog_filters(self):
        query = self.catalog_search_var.get().strip().lower()
        tipo = self.catalog_filter_var.get()
        sort_field = self.catalog_sort_field.get()
        sort_desc = self.catalog_sort_desc if isinstance(self.catalog_sort_desc, bool) else self.catalog_sort_desc.get()
        year_from = self.catalog_year_from.get().strip()
        year_to = self.catalog_year_to.get().strip()
        date_field = self.catalog_date_field.get()

        def entry_year_ok(entry):
            value = entry.get(date_field, "N/A")
            if value == "N/A" or len(value) < 4:
                return False
            try:
                year = int(value[:4])
                y_from = int(year_from) if year_from else None
                y_to = int(year_to) if year_to else None
                if y_from and year < y_from:
                    return False
                if y_to and year > y_to:
                    return False
                return True
            except ValueError:
                return False

        filtered = []
        for entry in self._catalog_results:
            name_ok = query in entry["Nome"].lower()
            type_ok = tipo == "Tutti" or entry["Tipo"] == tipo
            year_ok = entry_year_ok(entry) if (year_from or year_to) else True
            if name_ok and type_ok and year_ok:
                filtered.append(entry)

        if sort_field == "Nome":
            filtered.sort(key=lambda e: e["Nome"], reverse=sort_desc)
        elif sort_field == "Tipo":
            filtered.sort(key=lambda e: e["Tipo"], reverse=sort_desc)
        elif sort_field == "Data":
            from datetime import datetime
            def sort_key(e):
                v = e.get(date_field, "9999-12-31 00:00:00")
                try:
                    return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                except:
                    return datetime.max
            filtered.sort(key=sort_key, reverse=sort_desc)

        self._catalog_filtered = filtered
        self._show_catalog(filtered)


    def _show_catalog(self, entries):
        self.catalog_output.delete("1.0", tk.END)
        for entry in entries:
            self.catalog_output.insert(
                tk.END,
                f"Nome: {entry['Nome']}\n"
                f"  Tipo: {entry['Tipo']}\n"
                f"  ParentID: {entry['ParentID']}\n"
                f"  CNID: {entry['CNID']}\n"
                f"  Creato: {entry['Creato']}\n"
                f"  Modificato: {entry['Modificato']}\n"
                f"  Backup: {entry['Backup']}\n"
                + "-"*60 + "\n"
            )

    def _save_catalog_filtered(self):
        if not self._catalog_filtered:
            messagebox.showwarning("Vuoto", "Nessun risultato filtrato da salvare.")
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".txt", title="Salva output filtrato")
        if not out_path:
            return
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                for entry in self._catalog_filtered:
                    f.write(
                        f"Nome: {entry['Nome']}\n"
                        f"  Tipo: {entry['Tipo']}\n"
                        f"  ParentID: {entry['ParentID']}\n"
                        f"  CNID: {entry['CNID']}\n"
                        f"  Creato: {entry['Creato']}\n"
                        f"  Modificato: {entry['Modificato']}\n"
                        f"  Backup: {entry['Backup']}\n"
                        + "-"*60 + "\n"
                    )
            messagebox.showinfo("Salvato", f"File salvato in {out_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Salvataggio fallito:\n{e}")

    def _save_catalog_full(self):
        if not self._catalog_results:
            messagebox.showwarning("Vuoto", "Il catalog non è stato ancora caricato.")
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".txt", title="Salva catalog completo")
        if not out_path:
            return
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                for entry in self._catalog_results:
                    f.write(
                        f"Nome: {entry['Nome']}\n"
                        f"  Tipo: {entry['Tipo']}\n"
                        f"  ParentID: {entry['ParentID']}\n"
                        f"  CNID: {entry['CNID']}\n"
                        f"  Creato: {entry['Creato']}\n"
                        f"  Modificato: {entry['Modificato']}\n"
                        f"  Backup: {entry['Backup']}\n"
                        + "-"*60 + "\n"
                    )
            messagebox.showinfo("Salvato", f"Catalog completo salvato in {out_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il salvataggio:\n{e}")


    # ---------------- Delete Log Tab ------------------
    def _build_delete_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="HFS - Delete‑Log")
        ttk.Label(tab, text="📄 Analisi su file grezzo (spazio non allocato)", foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        ttk.Button(tab, text="Apri Delete‑Log", command=self._load_delete_log).pack(pady=5)
        self.delete_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.delete_output.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Button(tab, text="Salva Output", command=self._save_delete_log).pack(pady=5)
        self._delete_results = []

    def _load_delete_log(self):
        path = filedialog.askopenfilename(title="Seleziona file Delete Log", filetypes=[("Tutti i file", "*.*")])
        if not path:
            return
        self._delete_log_current_path = path  # ✅ salva path
        try:
            self._delete_results = parse_delete_log(path)
        except Exception as e:
            messagebox.showerror("Errore", str(e))
            return
        self.delete_output.delete("1.0", tk.END)
        self.delete_output.insert(tk.END, f"📂 File: {os.path.basename(path)} (clic per aprire)\n\n")
        self.delete_output.tag_add("delete_log_link", "1.0", "1.end")
        self.delete_output.tag_config("delete_log_link", foreground="blue", underline=True)
        self.delete_output.tag_bind("delete_log_link", "<Button-1>", lambda e, p=path: open_with_default_app(p))
        for off, typ, strings in self._delete_results:
            desc = type_descriptions.get(typ, "")
            label = f"{typ} ({desc})" if desc else typ
            self.delete_output.insert(tk.END, f"Offset: {off}  Tipo: {label}\n")
            for s in strings:
                self.delete_output.insert(tk.END, f"  - {s}\n")
            self.delete_output.insert(tk.END, "-" * 60 + "\n")

    def _save_delete_log(self):
        if not self._delete_results:
            messagebox.showwarning("Vuoto", "Nessun risultato da salvare.")
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".txt", title="Salva output")
        if not out_path:
            return
        with open(out_path, "w", encoding="utf-8") as f:
            for off, typ, strings in self._delete_results:
                desc = type_descriptions.get(typ, "")
                label = f"{typ} ({desc})" if desc else typ
                f.write(f"Offset: {off}  Tipo: {label}\n")
                for s in strings:
                    f.write(f"  - {s}\n")
                f.write("-" * 60 + "\n")
        messagebox.showinfo("Salvato", f"Output salvato in {out_path}")

    # ---------------- MDB Tab ------------------------
    def _build_mdb_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="HFS - MDB Header")
        ttk.Label(tab, text="💾 Analisi su intestazione del volume (floppy HFS)", foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        ttk.Button(tab, text="Apri MDB", command=self._load_mdb).pack(pady=5)
        self.mdb_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Courier New", 10))
        self.mdb_output.pack(fill="both", expand=True, padx=5, pady=5)

                # Pulsante Salva Output MDB
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill="x", pady=5)

        ttk.Button(
            button_frame,
            text="Salva Output MDB",
            command=lambda: self._save_text_widget(self.mdb_output)
        ).pack(side="right", padx=5)

    def _load_mdb(self):
        path = filedialog.askopenfilename(title="Seleziona file MDB", filetypes=[("Tutti i file", "*.*")])
        if not path:
            return
        self._mdb_current_path = path  # salva path file

        try:
            summary = parse_mdb(path)
            self.mdb_output.delete("1.0", tk.END)

            #  Mostra link cliccabile al file
            self.mdb_output.insert(tk.END, f"📂 File: {os.path.basename(path)} (clic per aprire)\n\n")
            self.mdb_output.tag_add("mdb_link", "1.0", "1.end")
            self.mdb_output.tag_config("mdb_link", foreground="blue", underline=True)
            self.mdb_output.tag_bind("mdb_link", "<Button-1>", lambda e, p=path: open_with_default_app(p))

            self.mdb_output.insert(tk.END, summary)
        except Exception as e:
            messagebox.showerror("Errore", str(e))


    # ---------------- Split Tab ----------------------
    def _build_split_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Split Word Segments")
        ttk.Label(tab, text="📄 Analisi di file binario grezzo per segmenti Word", foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))

        frm = ttk.Frame(tab)
        frm.pack(pady=5)
        ttk.Button(frm, text="Seleziona file binario", command=self._do_split).pack(side="left", padx=5)
        ttk.Label(frm, text="(Dividi automaticamente in corrispondenza dei marker di file Word)").pack(side="left")

        self.split_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.split_output.pack(fill="both", expand=True, padx=5, pady=5)

        # Pulsante salva in basso a destra
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill="x", pady=5)
        ttk.Button(
            button_frame,
            text="Salva elenco file",
            command=lambda: self._save_text_widget(self.split_output)
        ).pack(side="right", padx=5)

    def _do_split(self):
        in_path = filedialog.askopenfilename(title="Seleziona file da splittare")
        if not in_path:
            return

        out_dir = filedialog.askdirectory(title="Scegli dove salvare i file generati")
        if not out_dir:
            return

        markers = [b"\xFE\x37", b"\xFE\x34"]

        try:
            out_files = split_file_on_marker(in_path, markers, out_dir=out_dir)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante lo split:\n{e}")
            return

        self._split_current_path = in_path
        self.split_output.delete("1.0", tk.END)

        if not out_files:
            self.split_output.insert(tk.END, "Nessun segmento Word riconoscibile trovato.")
            return

        # File originale cliccabile
        self.split_output.insert(tk.END, f"📂 File originale: {os.path.basename(in_path)} (clic per aprire)\n")
        self.split_output.tag_add("split_link_orig", "1.0", "1.end")
        self.split_output.tag_config("split_link_orig", foreground="blue", underline=True)
        self.split_output.tag_bind("split_link_orig", "<Button-1>", lambda e, p=in_path: self._open_file_from_tag(p))

        self.split_output.insert(tk.END, f"\n📄 File generati ({len(out_files)}):\n\n")

        # Inserisci i file e registra i tag cliccabili
        for i, fpath in enumerate(out_files):
            fname = os.path.basename(fpath)
            link = ttk.Label(self.split_output, text=f"{i+1}. {fname}", foreground="blue", cursor="hand2", underline=True)
            link.bind("<Button-1>", lambda e, p=fpath: open_with_default_app(p))

            self.split_output.window_create(tk.END, window=link)
            self.split_output.insert(tk.END, "\n")  # newline dopo il widget




    # ---------------- Hex Decoder Tab ----------------
    def _build_hex_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="UTILS - Hex → ASCII Decoder")
        ttk.Label(tab, text="📄 Decodifica manuale di stringhe esadecimali", foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        self.hex_filter_control_codes = tk.BooleanVar()

        # Titolo
        ttk.Label(tab, text="Hex → ASCII Decoder", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=5, pady=(5, 2))

        # Checkbox: Nascondi caratteri di sistema
        ttk.Checkbutton(
            tab,
            text="Nascondi caratteri di sistema",
            variable=self.hex_filter_control_codes,
            command=self._decode_hex  #  attiva decodifica automatica
        ).pack(anchor="w", padx=5, pady=(0, 5))

        # Split pane: input sinistra, output destra
        pane = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True, padx=5, pady=5)

        # Area input esadecimale
        input_frame = ttk.Frame(pane)
        ttk.Label(input_frame, text="Input esadecimale").pack(anchor="w")
        self.hex_input = scrolledtext.ScrolledText(input_frame, wrap="word", font=("Courier New", 10), width=50)
        self.hex_input.pack(fill="both", expand=True)
        pane.add(input_frame, weight=1)

        # Area output ASCII
        output_frame = ttk.Frame(pane)
        ttk.Label(output_frame, text="Risultato decodificato").pack(anchor="w")
        self.hex_output = scrolledtext.ScrolledText(output_frame, wrap="word", font=("Courier New", 10), width=50)
        self.hex_output.pack(fill="both", expand=True)
        pane.add(output_frame, weight=1)

        # Pulsanti sotto
        button_row = ttk.Frame(tab)
        button_row.pack(fill="x", pady=(5, 10))

        # contenitore pulsanti a destra
        right_btns = ttk.Frame(button_row)
        right_btns.pack(side="right")

        ttk.Button(right_btns, text="Decodifica", command=self._decode_hex).pack(side="left", padx=5)
        ttk.Button(right_btns, text="Salva output", command=lambda: self._save_text_widget(self.hex_output)).pack(side="left", padx=5)


    def _decode_hex(self, *_):
        self.hex_input.update_idletasks()  # forza aggiornamento visivo
        src = self.hex_input.get("1.0", tk.END)
        exclude = EXCLUDED_HEX_CODES if self.hex_filter_control_codes.get() else None
        decoded = decode_custom_hex(src, exclude_hex=exclude)
        self.hex_output.delete("1.0", tk.END)
        self.hex_output.insert(tk.END, decoded)


    # ---------------- MCW Tab ------------------------
    def _build_mcw_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Word - MCW Hidden Text")
        ttk.Label(tab, text="📄 Estrazione da file Word per Mac (.mcw)", foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        ttk.Button(tab, text="Apri file", command=self._load_mcw).pack(pady=5)

        self.mcw_filter_control_codes = tk.BooleanVar()
        ttk.Checkbutton(
            tab,
            text="Nascondi caratteri di sistema",
            variable=self.mcw_filter_control_codes,
            command=self._render_mcw_view  #  aggiorna dinamicamente la vista
        ).pack(anchor="w", padx=5, pady=(0, 5))

                # Pulsante per aprire il file originale
        ttk.Button(
            tab,
            text="📂 Apri file con programma predefinito",
            command=lambda: open_with_default_app(self._mcw_current_path)
        ).pack(pady=(0, 5))

        self.mcw_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.mcw_output.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Button(tab, text="Salva testo", command=lambda: self._save_text_widget(self.mcw_output)).pack(pady=5)


    def _load_mcw(self):
        path = filedialog.askopenfilename(title="Seleziona file .mcw", filetypes=[("Tutti i file", "*.*")])
        if not path:
            return
        try:
            with open(path, "rb") as f:
                self._mcw_raw_data = f.read()
            self._mcw_current_path = path  #  salva il file corrente
            self._render_mcw_view()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare il file:\n{e}")


    def _render_mcw_view(self):
        if not hasattr(self, "_mcw_current_path"):
            return

        try:
            main_text, extra_text = extract_after_etx_mcw(
                self._mcw_current_path,
                exclude_hex=EXCLUDED_HEX_CODES if self.mcw_filter_control_codes.get() else None
            )
        except Exception as e:
            messagebox.showwarning("Errore", str(e))
            return

        self.mcw_output.delete("1.0", tk.END)
        self.mcw_output.insert(tk.END, "=== TESTO PRINCIPALE POST-ETX ===\n")
        self.mcw_output.insert(tk.END, main_text.strip() + "\n\n")
        if extra_text.strip():
            self.mcw_output.insert(tk.END, "=== TESTO EXTRA DOPO ETX ===\n")
            self.mcw_output.insert(tk.END, extra_text.strip())


    # ---------------- MCW Compare Tab (stesure) ------------------------
    def _build_mcw_compare_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Word - Confronto Stesure")

        ttk.Label(
            tab,
            text="📝 Confronto prima stesura (HEX) / stesura finale (LibreOffice)",
            foreground="#444",
            font=("Segoe UI", 9, "italic")
        ).pack(anchor="w", padx=5, pady=(5, 0))

        # scelta file .mcw
        path_frame = ttk.Frame(tab)
        path_frame.pack(fill="x", padx=5, pady=5)

        self.mcw_compare_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.mcw_compare_path_var, width=80).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            path_frame,
            text="Scegli file .mcw",
            command=self._select_mcw_for_compare
        ).pack(side="left", padx=5)

        ttk.Button(
            tab,
            text="Genera confronto stesure",
            command=self._run_mcw_compare
        ).pack(pady=(0, 5))

        # PanedWindow con due Text
        pane = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True, padx=5, pady=5)

        # colonna HEX
        left_frame = ttk.Frame(pane)
        ttk.Label(left_frame, text="Prima stesura (HEX)").pack(anchor="w")
        self.mcw_compare_hex_text = tk.Text(
            left_frame,
            wrap="none",
            font=("Courier New", 10)
        )
        self.mcw_compare_hex_text.pack(fill="both", expand=True)
        pane.add(left_frame, weight=1)

        # colonna DEF
        right_frame = ttk.Frame(pane)
        ttk.Label(right_frame, text="Stesura finale (DEF)").pack(anchor="w")
        self.mcw_compare_def_text = tk.Text(
            right_frame,
            wrap="none",
            font=("Courier New", 10)
        )
        self.mcw_compare_def_text.pack(fill="both", expand=True)
        pane.add(right_frame, weight=1)

        # Scrollbar verticale sincronizzata
        scroll_y = ttk.Scrollbar(tab, orient="vertical")
        scroll_y.pack(side="right", fill="y")

        def _on_scroll(*args):
            self.mcw_compare_hex_text.yview(*args)
            self.mcw_compare_def_text.yview(*args)
        scroll_y.config(command=_on_scroll)

        def _on_hex_yview(*args):
            scroll_y.set(*args)
            self.mcw_compare_def_text.yview_moveto(args[0])
        def _on_def_yview(*args):
            scroll_y.set(*args)
            self.mcw_compare_hex_text.yview_moveto(args[0])

        self.mcw_compare_hex_text.config(yscrollcommand=_on_hex_yview)
        self.mcw_compare_def_text.config(yscrollcommand=_on_def_yview)

        # Pulsanti salvataggio in basso
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(
            btn_frame,
            text="Salva HEX",
            command=self._save_compare_hex
        ).pack(side="right", padx=5)
        ttk.Button(
            btn_frame,
            text="Salva DEF",
            command=self._save_compare_def
        ).pack(side="right", padx=5)
        ttk.Button(
            btn_frame,
            text="Salva entrambe (HEX+DEF)",
            command=self._save_compare_both
        ).pack(side="right", padx=5)
        ttk.Button(
            btn_frame,
            text="Salva diff (HTML)",
            command=self._save_compare_diff_html
        ).pack(side="left", padx=5)

    def _select_mcw_for_compare(self):
        path = filedialog.askopenfilename(
            title="Seleziona file .mcw",
            filetypes=[("Tutti i file", "*.*")]
        )
        if path:
            self.mcw_compare_path_var.set(path)

    def _run_mcw_compare(self):
        path = self.mcw_compare_path_var.get().strip()
        if not path:
            messagebox.showwarning("Attenzione", "Seleziona prima un file .mcw.")
            return

        try:
            with open(path, "rb") as f:
                data = f.read()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile leggere il file:\n{e}")
            return

        try:
            prima_raw = estrai_prima_stesura_hex_da_mcw_bytes(data)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante estrazione prima stesura:\n{e}")
            return

        try:
            odt_path = converti_mcw_in_odt(path)
            finale_raw = estrai_testo_da_odt(odt_path)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante estrazione stesura finale con LibreOffice:\n{e}")
            return

        # normalizza (rimozione righe vuote)
        self._mcw_compare_prima = normalizza_rimuovi_righe_vuote(prima_raw)
        self._mcw_compare_finale = normalizza_rimuovi_righe_vuote(finale_raw)

        self._render_mcw_compare_view()

    def _render_mcw_compare_view(self):
        """
        Mostra nelle due colonne HEX/DEF le stesure numerate e con differenze evidenziate.
        """
        if not hasattr(self, "_mcw_compare_prima") or not hasattr(self, "_mcw_compare_finale"):
            return

        prima = self._mcw_compare_prima
        finale = self._mcw_compare_finale

        txt_hex = self.mcw_compare_hex_text
        txt_def = self.mcw_compare_def_text

        txt_hex.config(state="normal")
        txt_def.config(state="normal")
        txt_hex.delete("1.0", tk.END)
        txt_def.delete("1.0", tk.END)

        # definisci tag colori
        txt_hex.tag_configure("changed", background="#fff3b0")    # giallo
        txt_def.tag_configure("changed", background="#fff3b0")

        txt_hex.tag_configure("only_here", background="#f8d7da")  # rosso chiaro
        txt_def.tag_configure("only_here", background="#d4edda")  # verde chiaro

        # Normalizza righe per evitare falsi positivi (solo spazi/tab)
        lines_hex_original = prima.splitlines()
        lines_def_original = finale.splitlines()

        lines_hex = [normalizza_per_diff(l) for l in lines_hex_original]
        lines_def = [normalizza_per_diff(l) for l in lines_def_original]


        matcher = difflib.SequenceMatcher(None, lines_hex, lines_def)
        opcodes = matcher.get_opcodes()

        def ins_riga(widget: tk.Text, num: int, contenuto: str, tag: str | None = None):
            numero = f"{num:4d} | "
            start = widget.index("end-1c")
            widget.insert("end", numero + contenuto + "\n")
            end = widget.index("end-1c")
            if tag:
                widget.tag_add(tag, start, end)

        i_hex = 1
        i_def = 1

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                for k in range(i2 - i1):
                    ins_riga(txt_hex, i_hex, lines_hex[i1 + k])
                    ins_riga(txt_def, i_def, lines_def[j1 + k])
                    i_hex += 1
                    i_def += 1

            elif tag == "replace":
                blocco = max(i2 - i1, j2 - j1)
                for k in range(blocco):
                    h = lines_hex[i1 + k] if (i1 + k < i2) else ""
                    d = lines_def[j1 + k] if (j1 + k < j2) else ""
                    ins_riga(txt_hex, i_hex, h, tag="changed")
                    ins_riga(txt_def, i_def, d, tag="changed")
                    i_hex += 1
                    i_def += 1

            elif tag == "delete":
                for k in range(i2 - i1):
                    ins_riga(txt_hex, i_hex, lines_hex[i1 + k], tag="only_here")
                    ins_riga(txt_def, i_def, "", tag="only_here")
                    i_hex += 1
                    i_def += 1

            elif tag == "insert":
                for k in range(j2 - j1):
                    ins_riga(txt_hex, i_hex, "", tag="only_here")
                    ins_riga(txt_def, i_def, lines_def[j1 + k], tag="only_here")
                    i_hex += 1
                    i_def += 1

        txt_hex.config(state="disabled")
        txt_def.config(state="disabled")

    # ---------- salvataggi ----------
    def _save_compare_hex(self):
        if not hasattr(self, "_mcw_compare_prima"):
            messagebox.showwarning("Vuoto", "Nessuna prima stesura da salvare.")
            return
        out_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            title="Salva prima stesura (HEX)"
        )
        if not out_path:
            return
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(self._mcw_compare_prima)
        messagebox.showinfo("Salvato", f"Prima stesura salvata in:\n{out_path}")

    def _save_compare_def(self):
        if not hasattr(self, "_mcw_compare_finale"):
            messagebox.showwarning("Vuoto", "Nessuna stesura finale da salvare.")
            return
        out_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            title="Salva stesura finale (DEF)"
        )
        if not out_path:
            return
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(self._mcw_compare_finale)
        messagebox.showinfo("Salvato", f"Stesura finale salvata in:\n{out_path}")

    def _save_compare_both(self):
        if not (hasattr(self, "_mcw_compare_prima") and hasattr(self, "_mcw_compare_finale")):
            messagebox.showwarning("Vuoto", "Non ci sono stesure da salvare.")
            return
        base = filedialog.asksaveasfilename(
            defaultextension=".txt",
            title="Scegli nome base (verranno creati _HEX e _DEF)"
        )
        if not base:
            return
        base_path = Path(base)
        hex_path = base_path.with_name(base_path.stem + "_HEX.txt")
        def_path = base_path.with_name(base_path.stem + "_DEF.txt")
        with open(hex_path, "w", encoding="utf-8") as f:
            f.write(self._mcw_compare_prima)
        with open(def_path, "w", encoding="utf-8") as f:
            f.write(self._mcw_compare_finale)
        messagebox.showinfo(
            "Salvato",
            f"File salvati:\n{hex_path}\n{def_path}"
        )

    def _save_compare_diff_html(self):
        if not (hasattr(self, "_mcw_compare_prima") and hasattr(self, "_mcw_compare_finale")):
            messagebox.showwarning("Vuoto", "Non ci sono stesure da confrontare.")
            return
        out_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            title="Salva diff HTML"
        )
        if not out_path:
            return

        old_lines = self._mcw_compare_prima.splitlines()
        new_lines = self._mcw_compare_finale.splitlines()

        html = difflib.HtmlDiff(wrapcolumn=80).make_file(
            old_lines,
            new_lines,
            fromdesc="Prima stesura (HEX)",
            todesc="Stesura finale (LibreOffice)",
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        messagebox.showinfo("Salvato", f"Diff HTML salvato in:\n{out_path}")



#====================== TAB PER ANALISI DATE ==================#
    def _build_date_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="HFS - Analisi Date da Catalog")

        # Titolo descrittivo
        ttk.Label(tab, text="📅 Analisi temporale da file 'catalog'", foreground="#444", font=("Segoe UI", 9, "italic"))\
            .pack(anchor="w", padx=5, pady=(5, 0))

        # --- Scelta directory ---
        dir_frame = ttk.Frame(tab)
        dir_frame.pack(fill="x", padx=5, pady=5)

        self.date_dir_var = tk.StringVar()
        ttk.Entry(dir_frame, textvariable=self.date_dir_var, width=80).pack(side="left", fill="x", expand=True)
        ttk.Button(dir_frame, text="Scegli Cartella", command=self._browse_date_dir).pack(side="left", padx=5)

        # --- Scelta campo data ---
        field_frame = ttk.Frame(tab)
        field_frame.pack(fill="x", padx=5)

        ttk.Label(field_frame, text="Campo data da analizzare:").pack(side="left")
        self.date_field = tk.StringVar(value="Creato")
        ttk.Combobox(field_frame, textvariable=self.date_field,
                     values=["Creato", "Modificato", "Backup"], width=15).pack(side="left", padx=5)

        # --- Intervallo giorni tra Creato e Modificato ---
        range_frame = ttk.Frame(tab)
        range_frame.pack(fill="x", padx=5, pady=(0, 5))

        ttk.Label(range_frame, text="Intervallo giorni (Creato → Modificato):").pack(side="left")
        self.delta_min = tk.IntVar(value=0)
        self.delta_max = tk.IntVar(value=90)

        min_spin = ttk.Spinbox(range_frame, from_=0, to=365, textvariable=self.delta_min, width=5)
        min_spin.pack(side="left", padx=(5, 2))
        min_spin.bind("<FocusOut>", lambda e: self._plot_deltas())
        min_spin.bind("<Return>", lambda e: self._plot_deltas())

        ttk.Label(range_frame, text="a").pack(side="left")

        max_spin = ttk.Spinbox(range_frame, from_=0, to=365, textvariable=self.delta_max, width=5)
        max_spin.pack(side="left", padx=(2, 10))
        max_spin.bind("<FocusOut>", lambda e: self._plot_deltas())
        max_spin.bind("<Return>", lambda e: self._plot_deltas())



        # --- Pulsante analisi ---
        ttk.Button(tab, text="Estrai e Analizza", command=self._run_date_analysis).pack(pady=5)

        # --- Output testuale ---
        self.date_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.date_output.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Pulsanti export ---
        out_frame = ttk.Frame(tab)
        out_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(out_frame, text="Salva CSV", command=self._save_date_csv).pack(side="right", padx=5)
        ttk.Button(out_frame, text="Grafico Annuale", command=self._plot_annual).pack(side="left", padx=5)
        ttk.Button(out_frame, text="Grafico Mensile", command=self._plot_monthly).pack(side="left", padx=5)
        ttk.Button(out_frame, text="Distribuzione intervalli", command=self._plot_deltas).pack(side="left", padx=5)

        # Placeholder per dataframe risultati
        self.date_df = None

    def _browse_date_dir(self):
        folder = filedialog.askdirectory(title="Seleziona una cartella con file catalog")
        if folder:
            self.date_dir_var.set(folder)

    def _run_date_analysis(self):
        folder = self.date_dir_var.get()
        field = self.date_field.get()
        if not folder:
            messagebox.showwarning("Attenzione", "Seleziona una cartella valida.")
            return

        try:
            df = estrai_date_catalog(folder)
            if df.empty:
                raise ValueError("Nessun dato valido trovato.")
            self.date_df = df
        except Exception as e:
            messagebox.showerror("Errore", str(e))
            return

        self.date_output.delete("1.0", tk.END)
        self.date_output.insert(tk.END, f"Totale file trovati: {len(df)}\n")

        try:
            serie = pd.to_datetime(df[field], errors="coerce").dropna()
            self.date_output.insert(tk.END, f"Intervallo date: {serie.min().date()} → {serie.max().date()}\n")
        except:
            self.date_output.insert(tk.END, "Errore durante l'analisi delle date.\n")

    def _save_date_csv(self):
        import pandas as pd
        if self.date_df is None or self.date_df.empty:
            messagebox.showwarning("Vuoto", "Nessun dato da salvare.")
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".csv")
        if not out_path:
            return
        self.date_df.to_csv(out_path, index=False, encoding="utf-8")
        messagebox.showinfo("Salvato", f"CSV salvato in {out_path}")

    def _plot_annual(self):
        import pandas as pd
        import matplotlib.pyplot as plt
        if self.date_df is None:
            return
        field = self.date_field.get()
        serie = pd.to_datetime(self.date_df[field], errors="coerce").dropna()
        years = serie.dt.year.value_counts().sort_index()
        years.plot(kind="bar")
        plt.title(f"Distribuzione per Anno ({field})")
        plt.xlabel("Anno")
        plt.ylabel("Numero di file")
        plt.tight_layout()
        plt.show()

    def _plot_monthly(self):
        import pandas as pd
        import matplotlib.pyplot as plt
        if self.date_df is None:
            return

        field = self.date_field.get()
        serie = pd.to_datetime(self.date_df[field], errors="coerce").dropna()

        # Raggruppa per anno-mese e converte in stringa es. "2023-01"
        grouped = serie.dt.to_period("M").astype(str).value_counts().sort_index()

        # Plot
        grouped.plot(kind="bar", figsize=(10, 4))
        plt.title(f"Distribuzione Mensile ({field})")
        plt.xlabel("Mese")
        plt.ylabel("Numero di file")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.show()


    def _plot_deltas(self):
        import pandas as pd
        import matplotlib.pyplot as plt
        if self.date_df is None:
            return

        try:
            min_days = self.delta_min.get()
            max_days = self.delta_max.get()

            serie = pd.to_datetime(self.date_df["Creato"], errors="coerce")
            delta = pd.to_datetime(self.date_df["Modificato"], errors="coerce") - serie
            delta_days = delta.dt.total_seconds().dropna() / 86400

            # Filtra per intervallo selezionato
            filtered = delta_days[(delta_days >= min_days) & (delta_days <= max_days)]
            if filtered.empty:
                messagebox.showinfo("Nessun risultato", "Nessun file nell'intervallo selezionato.")
                return

            filtered.hist(bins=30)
            plt.title(f"Intervallo Creato→Modificato ({min_days}-{max_days} giorni)")
            plt.xlabel("Giorni")
            plt.ylabel("Frequenza")
            plt.tight_layout()
            plt.show()

        except Exception as e:
            messagebox.showwarning("Errore", f"Problema durante il calcolo:\n{e}")


# ------------- Utils -----------------------------
    def _open_guida_tab(self):
        # Crea tab solo se non già presente
        if hasattr(self, "_guida_tab"):
            self.notebook.select(self._guida_tab)
            return

        self._guida_tab = ttk.Frame(self.notebook)
        self.notebook.add(self._guida_tab, text="Guida")
        self.notebook.select(self._guida_tab)

        guida_text = scrolledtext.ScrolledText(self._guida_tab, wrap="word", font=("Segoe UI", 10))
        guida_text.pack(fill="both", expand=True, padx=10, pady=10)

        guida_text.insert(tk.END,
    """eFFe Quadro - Forensic Toolkit

Il programma consente analisi forensi su volumi HFS e file Word per Mac.
Ogni scheda del toolkit ha un ruolo e richiede un input specifico.

────────────────────────────────────────────────────────
🔗 Strumenti consigliati
────────────────────────────────────────────────────────
    Per visualizzare in modo preliminare il contenuto esadecimale di un file,
    puoi usare il sito web gratuito:
    """)

        # Link cliccabile a hexed.it
        start = guida_text.index(tk.INSERT)
        guida_text.insert(tk.END, "https://hexed.it\n")
        end = guida_text.index(tk.INSERT)
        guida_text.tag_add("hexed_link", start, end)
        guida_text.tag_config("hexed_link", foreground="blue", underline=True)
        guida_text.tag_bind("hexed_link", "<Button-1>", lambda e: webbrowser.open_new("https://hexed.it"))

        # Resto della guida
        guida_text.insert(tk.END,
    """

────────────────────────────────────────────────────────
📂 Allocation & Extents
────────────────────────────────────────────────────────
Tipo di input accettato:
  - Bitmap di allocazione (es. file chiamato 'allocation')
  - File Extents Overflow (es. 'extents')

Dove si trova:
  - Entrambi estratti da immagini di floppy o partizioni HFS.

Scopo:
  - Analizza lo stato di allocazione dei blocchi e ricostruisce le estensioni dei file. Utile per trovare spazio libero o file frammentati.

────────────────────────────────────────────────────────
🗂️ Catalog
────────────────────────────────────────────────────────
Tipo di input accettato:
  - File 'catalog' estratto da un floppy o supporto HFS

Dove si trova:
  - Primo livello all'interno di una cartella root.

Scopo:
  - Sintesi strutturata del contenuto di una cartella o intero volume HFS.
  - Visualizza file, cartelle e thread con metadati: nome, CNID, ParentID, data creazione/modifica/backup.
  - Permette filtri, ordinamento e salvataggio dell’output.

────────────────────────────────────────────────────────
🧹 Delete-Log
────────────────────────────────────────────────────────
Tipo di input accettato:
  - File chiamato 'delete-log'.

Dove si trova:
  - Secondo livello all'interno di una cartella root. Non sempre è presente

Scopo:
  - Individua frammenti di file Word cancellati tramite scansione a blocchi (256 byte).
  - Evidenzia intestazioni Word (MSWDWDBN, MSWDWTMP) e stringhe ASCII residue.

────────────────────────────────────────────────────────
📑 MDB Header
────────────────────────────────────────────────────────
Tipo di input accettato:
  - File 'mdb', 'mdb backup'.

Dove si trova:
  - Primo livello all'interno di una cartella root.

Scopo:
  - Estrae parametri del file system (firma BD, date, dimensioni, etichetta volume). A etichetta indica il nome con cui un supporto (es. floppy) è stato originariamente chiamato.
  - Utile per datare il volume, identificare provenienza o stato logico del floppy.

────────────────────────────────────────────────────────
✂️ Split Word Segments
────────────────────────────────────────────────────────
Tipo di input accettato:
  - File binario grezzo da spazio non allocato, solitamente nome costituito da 4 cifre (es. 1794)

Dove si trova:
  - All'interno della cartella [unallocated space]

Scopo:
  - Divide automaticamente segmenti Word separati da marker specifici.
  - Ogni segmento viene salvato come .odt numerato.

────────────────────────────────────────────────────────
🧮 Hex → ASCII Decoder
────────────────────────────────────────────────────────
Tipo di input accettato:
  - Inserimento manuale di stringhe esadecimali

Dove si trova:
  - Copiato da altri strumenti (es. hex editor) o output grezzi.

Scopo:
  - Decodifica esadecimale secondo mappa custom Word/Mac.
  - Utile per testare blocchi di testo isolati o mappare simboli.

────────────────────────────────────────────────────────
📜 MCW Hidden Text
────────────────────────────────────────────────────────
Tipo di input accettato:
  - File di testo di tipo Microsoft Word per Macintosh

Dove si trova:
  - Un file testuale qualsiasi all'interno delle cartelle/floppy.

Scopo:
  - Estrae testo nascosto oltre l’area principale (post-etx).
  - Opzione per nascondere caratteri di controllo e mostrare solo testo utile.
"""
        )


        guida_text.configure(state="disabled")




    def _save_text_widget(self, widget: tk.Text):
        txt = widget.get("1.0", tk.END).strip()
        if not txt:
            messagebox.showwarning("Vuoto", "Nulla da salvare.")
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not out_path:
            return
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(txt)
        messagebox.showinfo("Salvato", f"File salvato in {out_path}")
