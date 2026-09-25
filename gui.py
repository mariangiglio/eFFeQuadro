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
    record_type_label,
)
from i18n import t, get_language, set_language, LANGUAGES


# =============================================================================
#                                START GUI
# =============================================================================

class HFSToolkitGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.geometry("1100x750")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        """Costruisce menu e schede nella lingua corrente."""
        root = self.root
        root.title(t("app_title"))

        # stato iniziale (evita errori se si usano i pulsanti prima di caricare un file)
        self._catalog_results = []
        self._catalog_filtered = []

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

    def _switch_language(self, lang):
        """Cambia lingua e ricostruisce l'interfaccia (i risultati aperti vengono chiusi)."""
        if lang == get_language():
            return
        if not messagebox.askokcancel(t("lang_title"), t("lang_confirm")):
            self._language_var.set(get_language())
            return
        set_language(lang)
        root = self.root
        self.notebook.destroy()
        self.__dict__.clear()   # azzera tutto lo stato della sessione precedente
        self.root = root
        self._build_ui()


    def _open_file_from_tag(self, path, *_):
        open_with_default_app(path)

    def _make_combo(self, parent, options, default, width):
        """
        Combobox con etichette tradotte e codici interni fissi.
        options: lista di (codice interno, chiave i18n).
        Restituisce (widget, funzione che restituisce il codice selezionato).
        """
        labels = [t(key) for _, key in options]
        label_to_code = {t(key): code for code, key in options}
        var = tk.StringVar(value=t(dict(options)[default]))
        combo = ttk.Combobox(parent, textvariable=var, values=labels, width=width)
        combo._var = var  # mantiene il riferimento alla variabile
        return combo, lambda: label_to_code.get(var.get(), default)

    def _add_main_menu(self):
        THEME_LABELS = {
            name: t("theme_" + name)
            for name in ("aquativo", "adapta", "black", "blue", "breeze", "clearlooks",
                         "itft1", "kroc", "plastik", "radiance", "xpnative")
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
        guida_menu.add_command(label=t("menu_open_guide"), command=self._open_guida_tab)
        menubar.add_cascade(label=t("menu_guide"), menu=guida_menu)

        # --- Menu Credits ---
        credits_menu = tk.Menu(menubar, tearoff=0)
        credits_menu.add_command(
            label=t("menu_about"),
            command=lambda: messagebox.showinfo("Credits", t("credits_text"))
        )
        menubar.add_cascade(label=t("menu_credits"), menu=credits_menu)

        # --- Menu Temi ---
        theme_menu = tk.Menu(menubar, tearoff=0)
        for theme_name in sorted(THEME_LABELS):
            label = THEME_LABELS[theme_name]
            theme_menu.add_command(label=label, command=lambda theme=theme_name: self.root.set_theme(theme))
        menubar.add_cascade(label=t("menu_themes"), menu=theme_menu)

        # --- Menu Lingua ---
        language_menu = tk.Menu(menubar, tearoff=0)
        self._language_var = tk.StringVar(value=get_language())
        for code, name in LANGUAGES.items():
            language_menu.add_radiobutton(
                label=name, value=code, variable=self._language_var,
                command=lambda c=code: self._switch_language(c)
            )
        menubar.add_cascade(label=t("menu_language"), menu=language_menu)



#------------------- File info tab -------------------#
    def _build_info_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=t("tab_info"))
        ttk.Label(tab, text=t("info_desc"), foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        # Selettore file
        path_frame = ttk.Frame(tab)
        path_frame.pack(fill="x", padx=5, pady=5)

        self.info_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.info_path_var, width=80).pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text=t("choose_file"), command=self._select_info_file).pack(side="left", padx=5)

        # Output area
        self.info_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.info_output.pack(fill="both", expand=True, padx=5, pady=5)

    def _select_info_file(self):
        path = filedialog.askopenfilename(title=t("select_file_to_analyze"))
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
            self.info_output.insert(tk.END, t("error_prefix", e=e))
            return

        name = os.path.basename(path).lower()
        known_files = {
            "catalog": "Catalog B-tree",
            "mdb": "MDB (Master Directory Block)",
            "extents": "Extents Overflow",
            "allocation": "Allocation Bitmap",
            "delete": "Delete Log",
            "desktop db": t("sys_desktop_db"),
            "desktop": t("sys_desktop"),
            "finder.dat": t("sys_finder"),
            ".trash": t("sys_trash"),
        }

        # Check by filename
        for key, label in known_files.items():
            if key in name:
                self.info_output.insert(tk.END, t("recognized", label=label))
                break

        # Check magic bytes
        magic_hex = binascii.hexlify(data).upper()
        # firma -> chiave del testo (vedi i18n.py)
        markers = {
            b"\xFE\x37\x00\x23": "word5",
            b"\xFE\x37\x00\x1C": "word4",
            b"\xFE\x37\x00\x1B": "word4x",
            b"\xFE\x37\x00\xA4": "word4x",
            b"\xFE\x37\x00\x05": "word3x",
            b"\xFE\x34\x00\x00": "word3",
            b"\xFE\x32\x00": "write_atari",
        }
        # note aggiuntive per versione (5.1 e 6 per future firme)
        version_notes = {
            "word5": "word5_notes",
            "word51": "word51_notes",
            "word6": "word6_notes",
        }

        found = False
        for sig, version_key in markers.items():
            if data.startswith(sig):
                found = True
                self.info_output.insert(tk.END, t("word_recognized", version=t(version_key)))
                if version_key in version_notes:
                    self.info_output.insert(tk.END, t(version_notes[version_key]))
                break

        if not found:
            # Heuristic for textual content
            ascii_chars = sum(c < 128 and chr(c).isprintable() for c in data)
            if data and ascii_chars / len(data) > 0.6:
                self.info_output.insert(tk.END, t("probably_text"))
            else:
                self.info_output.insert(tk.END, t("type_uncertain"))


    # ---------------- Allocation Tab ------------------
    def _build_allocation_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=t("tab_alloc"))
        ttk.Label(tab, text=t("alloc_desc"), foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text=t("open_alloc"), command=self._load_allocation_bitmap).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=t("open_extents"), command=self._load_extents_overflow).pack(side="left", padx=5)

        self.alloc_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.alloc_output.pack(fill="both", expand=True, padx=5, pady=5)

                # Pulsante Salva Output (in basso a destra)
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill="x", pady=5)

        ttk.Button(
            button_frame,
            text=t("save_output"),
            command=lambda: self._save_text_widget(self.alloc_output)
        ).pack(side="right", padx=5)


    def _load_allocation_bitmap(self):
        path = filedialog.askopenfilename(title=t("select_alloc"))
        if not path:
            return
        used, free, total = parse_allocation_bitmap(path)
        self.alloc_output.delete("1.0", tk.END)
        self.alloc_output.insert(tk.END, t("alloc_summary", total=total, used=used, free=free))
        self.alloc_output.insert(tk.END, t("click_to_open", name=os.path.basename(path)) + "\n")
        self.alloc_output.tag_add("alloc_link", "5.0", "5.end")
        self.alloc_output.tag_config("alloc_link", foreground="blue", underline=True)
        self.alloc_output.tag_bind("alloc_link", "<Button-1>", lambda e, p=path: open_with_default_app(p))

    def _load_extents_overflow(self):
        path = filedialog.askopenfilename(title=t("select_extents"))
        if not path:
            return

        try:
            results = parse_extents_overflow(path)
        except Exception as e:
            messagebox.showerror(t("error"), t("err_parsing", e=e))
            return

        self.alloc_output.delete("1.0", tk.END)

        # 📂 Link al file
        self.alloc_output.insert(tk.END, t("click_to_open", name=os.path.basename(path)) + "\n\n")
        self.alloc_output.tag_add("extents_link", "1.0", "1.end")
        self.alloc_output.tag_config("extents_link", foreground="blue", underline=True)
        self.alloc_output.tag_bind("extents_link", "<Button-1>", lambda e, p=path: open_with_default_app(p))

        if not results:
            self.alloc_output.insert(tk.END, t("extents_none"))
            return

        # 📦 Scrivi tutti i risultati
        for r in results:
            self.alloc_output.insert(
                tk.END,
                t("extents_header", cnid=r['CNID'], fork=r['Fork'],
                  fmt=r.get('Format', 'HFS'), fblock=r.get('FileBlock', '-'))
            )
            for i, (start, count) in enumerate(r['Extents'], 1):
                self.alloc_output.insert(tk.END, t("extent_line", i=i, start=start, count=count))
            self.alloc_output.insert(tk.END, "-" * 50 + "\n")


    # ---------------- Catalog Tab ---------------------
    def _build_catalog_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=t("tab_catalog"))
        ttk.Label(tab, text=t("catalog_desc"), foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        ttk.Button(tab, text=t("open_catalog"), command=self._load_catalog).pack(pady=5, padx=5)

        filter_frame = ttk.Frame(tab)
        filter_frame.pack(fill="x", padx=5, pady=5)

        # --- Filtro per nome e tipo ---
        ttk.Label(filter_frame, text=t("search_name")).pack(side="left")
        self.catalog_search_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.catalog_search_var, width=20).pack(side="left", padx=5)

        ttk.Label(filter_frame, text=t("filter_type")).pack(side="left", padx=(10, 2))
        combo, self._catalog_type_code = self._make_combo(
            filter_frame,
            [("all", "opt_all"), ("file", "rectype_file"), ("folder", "rectype_folder"),
             ("folder_thread", "rectype_folder_thread"), ("file_thread", "rectype_file_thread")],
            "all", 15)
        combo.pack(side="left")

        # --- Filtro per anno ---
        ttk.Label(filter_frame, text=t("year_from")).pack(side="left", padx=(10, 2))
        self.catalog_year_from = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.catalog_year_from, width=6).pack(side="left")

        ttk.Label(filter_frame, text=t("year_to")).pack(side="left")
        self.catalog_year_to = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.catalog_year_to, width=6).pack(side="left")

        # --- Campo data da analizzare ---
        ttk.Label(filter_frame, text=t("date_field")).pack(side="left", padx=(10, 2))
        combo, self._catalog_date_code = self._make_combo(
            filter_frame,
            [("Created", "field_created"), ("Modified", "field_modified"), ("Backup", "field_backup")],
            "Created", 12)
        combo.pack(side="left")

        # --- Ordinamento ---
        ttk.Label(filter_frame, text=t("sort_by")).pack(side="left", padx=(10, 2))
        combo, self._catalog_sort_code = self._make_combo(
            filter_frame,
            [("name", "sort_name"), ("type", "sort_type"), ("date", "sort_date")],
            "name", 10)
        combo.pack(side="left")

        self.catalog_sort_desc = False  # booleano invece di BooleanVar
        self._sort_dir_button = ttk.Button(filter_frame, text=t("sort_asc"), command=self._toggle_sort_dir)
        self._sort_dir_button.pack(side="left", padx=5)

        # --- Bottone filtro ---
        ttk.Button(filter_frame, text=t("apply_filter"), command=self._apply_catalog_filters).pack(side="left", padx=10)

        # 1. Area di testo per risultati
        self.catalog_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.catalog_output.pack(fill="both", expand=True, padx=5, pady=5)

        # 2. Pulsante Salva
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill="x", pady=5)

        ttk.Button(button_frame, text=t("save_filtered"), command=self._save_catalog_filtered).pack(side="right", padx=5)
        ttk.Button(button_frame, text=t("save_full_catalog"), command=self._save_catalog_full).pack(side="right", padx=5)



    def _toggle_sort_dir(self):
        self.catalog_sort_desc = not self.catalog_sort_desc
        new_text = t("sort_desc") if self.catalog_sort_desc else t("sort_asc")
        self._sort_dir_button.config(text=new_text)
        self._apply_catalog_filters()


    def _load_catalog(self):
        path = filedialog.askopenfilename(title=t("select_catalog"), filetypes=[(t("all_files"), "*.*")])
        if not path:
            return
        try:
            df = parse_catalog_btree(path)
            self._catalog_results = df
            self._catalog_filtered = df.copy()
            self._catalog_current_path = path

            self.catalog_output.delete("1.0", tk.END)
            self.catalog_output.insert(tk.END, t("click_to_open", name=os.path.basename(path)) + "\n\n")
            self.catalog_output.tag_add("catalog_link", "1.0", "1.end")
            self.catalog_output.tag_config("catalog_link", foreground="blue", underline=True)
            self.catalog_output.tag_bind("catalog_link", "<Button-1>", lambda e, p=path: open_with_default_app(p))

            self._show_catalog(df)
        except Exception as e:
            messagebox.showerror(t("error"), t("err_parsing", e=e))



    def _apply_catalog_filters(self):
        query = self.catalog_search_var.get().strip().lower()
        tipo = self._catalog_type_code()
        sort_field = self._catalog_sort_code()
        sort_desc = self.catalog_sort_desc if isinstance(self.catalog_sort_desc, bool) else self.catalog_sort_desc.get()
        year_from = self.catalog_year_from.get().strip()
        year_to = self.catalog_year_to.get().strip()
        date_field = self._catalog_date_code()

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
            name_ok = query in entry["Name"].lower()
            type_ok = tipo == "all" or entry["Type"] == tipo
            year_ok = entry_year_ok(entry) if (year_from or year_to) else True
            if name_ok and type_ok and year_ok:
                filtered.append(entry)

        if sort_field == "name":
            filtered.sort(key=lambda e: e["Name"], reverse=sort_desc)
        elif sort_field == "type":
            filtered.sort(key=lambda e: record_type_label(e), reverse=sort_desc)
        elif sort_field == "date":
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
            self.catalog_output.insert(tk.END, self._format_catalog_entry(entry))

    def _format_catalog_entry(self, entry):
        """Testo di una voce del Catalog, nella lingua corrente."""
        return t(
            "catalog_entry",
            name=entry["Name"],
            type=record_type_label(entry),
            parent=entry["ParentID"],
            cnid=entry["CNID"],
            created=entry["Created"],
            modified=entry["Modified"],
            backup=entry["Backup"],
        ) + "-" * 60 + "\n"

    def _save_catalog_filtered(self):
        if not self._catalog_filtered:
            messagebox.showwarning(t("empty"), t("no_filtered"))
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".txt", title=t("save_filtered_title"))
        if not out_path:
            return
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                for entry in self._catalog_filtered:
                    f.write(self._format_catalog_entry(entry))
            messagebox.showinfo(t("saved"), t("file_saved_in", path=out_path))
        except Exception as e:
            messagebox.showerror(t("error"), t("save_failed", e=e))

    def _save_catalog_full(self):
        if not self._catalog_results:
            messagebox.showwarning(t("empty"), t("catalog_not_loaded"))
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".txt", title=t("save_full_title"))
        if not out_path:
            return
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                for entry in self._catalog_results:
                    f.write(self._format_catalog_entry(entry))
            messagebox.showinfo(t("saved"), t("full_saved", path=out_path))
        except Exception as e:
            messagebox.showerror(t("error"), t("err_saving", e=e))


    # ---------------- Delete Log Tab ------------------
    def _build_delete_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=t("tab_delete"))
        ttk.Label(tab, text=t("delete_desc"), foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        ttk.Button(tab, text=t("open_delete"), command=self._load_delete_log).pack(pady=5)
        self.delete_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.delete_output.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Button(tab, text=t("save_output"), command=self._save_delete_log).pack(pady=5)
        self._delete_results = []

    def _load_delete_log(self):
        path = filedialog.askopenfilename(title=t("select_delete"), filetypes=[(t("all_files"), "*.*")])
        if not path:
            return
        self._delete_log_current_path = path  # ✅ salva path
        try:
            self._delete_results = parse_delete_log(path)
        except Exception as e:
            messagebox.showerror(t("error"), str(e))
            return
        self.delete_output.delete("1.0", tk.END)
        self.delete_output.insert(tk.END, t("click_to_open", name=os.path.basename(path)) + "\n\n")
        self.delete_output.tag_add("delete_log_link", "1.0", "1.end")
        self.delete_output.tag_config("delete_log_link", foreground="blue", underline=True)
        self.delete_output.tag_bind("delete_log_link", "<Button-1>", lambda e, p=path: open_with_default_app(p))
        for off, typ, strings in self._delete_results:
            desc = t(type_descriptions[typ]) if typ in type_descriptions else ""
            label = f"{typ} ({desc})" if desc else typ
            self.delete_output.insert(tk.END, t("delete_entry", off=off, label=label))
            for s in strings:
                self.delete_output.insert(tk.END, f"  - {s}\n")
            self.delete_output.insert(tk.END, "-" * 60 + "\n")

    def _save_delete_log(self):
        if not self._delete_results:
            messagebox.showwarning(t("empty"), t("no_results_to_save"))
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".txt", title=t("save_output_lc"))
        if not out_path:
            return
        with open(out_path, "w", encoding="utf-8") as f:
            for off, typ, strings in self._delete_results:
                desc = t(type_descriptions[typ]) if typ in type_descriptions else ""
                label = f"{typ} ({desc})" if desc else typ
                f.write(t("delete_entry", off=off, label=label))
                for s in strings:
                    f.write(f"  - {s}\n")
                f.write("-" * 60 + "\n")
        messagebox.showinfo(t("saved"), t("output_saved_in", path=out_path))

    # ---------------- MDB Tab ------------------------
    def _build_mdb_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=t("tab_mdb"))
        ttk.Label(tab, text=t("mdb_desc"), foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        ttk.Button(tab, text=t("open_mdb"), command=self._load_mdb).pack(pady=5)
        self.mdb_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Courier New", 10))
        self.mdb_output.pack(fill="both", expand=True, padx=5, pady=5)

                # Pulsante Salva Output MDB
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill="x", pady=5)

        ttk.Button(
            button_frame,
            text=t("save_mdb"),
            command=lambda: self._save_text_widget(self.mdb_output)
        ).pack(side="right", padx=5)

    def _load_mdb(self):
        path = filedialog.askopenfilename(title=t("select_mdb"), filetypes=[(t("all_files"), "*.*")])
        if not path:
            return
        self._mdb_current_path = path  # salva path file

        try:
            summary = parse_mdb(path)
            self.mdb_output.delete("1.0", tk.END)

            #  Mostra link cliccabile al file
            self.mdb_output.insert(tk.END, t("click_to_open", name=os.path.basename(path)) + "\n\n")
            self.mdb_output.tag_add("mdb_link", "1.0", "1.end")
            self.mdb_output.tag_config("mdb_link", foreground="blue", underline=True)
            self.mdb_output.tag_bind("mdb_link", "<Button-1>", lambda e, p=path: open_with_default_app(p))

            self.mdb_output.insert(tk.END, summary)
        except Exception as e:
            messagebox.showerror(t("error"), str(e))


    # ---------------- Split Tab ----------------------
    def _build_split_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=t("tab_split"))
        ttk.Label(tab, text=t("split_desc"), foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))

        frm = ttk.Frame(tab)
        frm.pack(pady=5)
        ttk.Button(frm, text=t("select_binary"), command=self._do_split).pack(side="left", padx=5)
        ttk.Label(frm, text=t("split_hint")).pack(side="left")

        self.split_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.split_output.pack(fill="both", expand=True, padx=5, pady=5)

        # Pulsante salva in basso a destra
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill="x", pady=5)
        ttk.Button(
            button_frame,
            text=t("save_file_list"),
            command=lambda: self._save_text_widget(self.split_output)
        ).pack(side="right", padx=5)

    def _do_split(self):
        in_path = filedialog.askopenfilename(title=t("select_to_split"))
        if not in_path:
            return

        out_dir = filedialog.askdirectory(title=t("choose_out_dir"))
        if not out_dir:
            return

        markers = [b"\xFE\x37", b"\xFE\x34"]

        try:
            out_files = split_file_on_marker(in_path, markers, out_dir=out_dir)
        except Exception as e:
            messagebox.showerror(t("error"), t("err_split", e=e))
            return

        self._split_current_path = in_path
        self.split_output.delete("1.0", tk.END)

        if not out_files:
            self.split_output.insert(tk.END, t("no_segments"))
            return

        # File originale cliccabile
        self.split_output.insert(tk.END, t("original_file", name=os.path.basename(in_path)))
        self.split_output.tag_add("split_link_orig", "1.0", "1.end")
        self.split_output.tag_config("split_link_orig", foreground="blue", underline=True)
        self.split_output.tag_bind("split_link_orig", "<Button-1>", lambda e, p=in_path: self._open_file_from_tag(p))

        self.split_output.insert(tk.END, t("generated_files", n=len(out_files)))

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
        self.notebook.add(tab, text=t("tab_hex"))
        ttk.Label(tab, text=t("hex_desc"), foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        self.hex_filter_control_codes = tk.BooleanVar()

        # Titolo
        ttk.Label(tab, text=t("hex_title"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=5, pady=(5, 2))

        # Checkbox: Nascondi caratteri di sistema
        ttk.Checkbutton(
            tab,
            text=t("hide_system_chars"),
            variable=self.hex_filter_control_codes,
            command=self._decode_hex  #  attiva decodifica automatica
        ).pack(anchor="w", padx=5, pady=(0, 5))

        # Split pane: input sinistra, output destra
        pane = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True, padx=5, pady=5)

        # Area input esadecimale
        input_frame = ttk.Frame(pane)
        ttk.Label(input_frame, text=t("hex_input")).pack(anchor="w")
        self.hex_input = scrolledtext.ScrolledText(input_frame, wrap="word", font=("Courier New", 10), width=50)
        self.hex_input.pack(fill="both", expand=True)
        pane.add(input_frame, weight=1)

        # Area output ASCII
        output_frame = ttk.Frame(pane)
        ttk.Label(output_frame, text=t("decoded_result")).pack(anchor="w")
        self.hex_output = scrolledtext.ScrolledText(output_frame, wrap="word", font=("Courier New", 10), width=50)
        self.hex_output.pack(fill="both", expand=True)
        pane.add(output_frame, weight=1)

        # Pulsanti sotto
        button_row = ttk.Frame(tab)
        button_row.pack(fill="x", pady=(5, 10))

        # contenitore pulsanti a destra
        right_btns = ttk.Frame(button_row)
        right_btns.pack(side="right")

        ttk.Button(right_btns, text=t("decode"), command=self._decode_hex).pack(side="left", padx=5)
        ttk.Button(right_btns, text=t("save_output_lc"), command=lambda: self._save_text_widget(self.hex_output)).pack(side="left", padx=5)


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
        self.notebook.add(tab, text=t("tab_mcw"))
        ttk.Label(tab, text=t("mcw_desc"), foreground="#444", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=5, pady=(5, 0))


        ttk.Button(tab, text=t("open_file"), command=self._load_mcw).pack(pady=5)

        self.mcw_filter_control_codes = tk.BooleanVar()
        ttk.Checkbutton(
            tab,
            text=t("hide_system_chars"),
            variable=self.mcw_filter_control_codes,
            command=self._render_mcw_view  #  aggiorna dinamicamente la vista
        ).pack(anchor="w", padx=5, pady=(0, 5))

                # Pulsante per aprire il file originale
        ttk.Button(
            tab,
            text=t("open_default_app"),
            command=self._open_mcw_default
        ).pack(pady=(0, 5))

        self.mcw_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.mcw_output.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Button(tab, text=t("save_text"), command=lambda: self._save_text_widget(self.mcw_output)).pack(pady=5)


    def _open_mcw_default(self):
        if not hasattr(self, "_mcw_current_path"):
            messagebox.showwarning(t("warning"), t("mcw_no_file"))
            return
        open_with_default_app(self._mcw_current_path)

    def _load_mcw(self):
        path = filedialog.askopenfilename(title=t("select_mcw"), filetypes=[(t("all_files"), "*.*")])
        if not path:
            return
        try:
            with open(path, "rb") as f:
                self._mcw_raw_data = f.read()
            self._mcw_current_path = path  #  salva il file corrente
            self._render_mcw_view()
        except Exception as e:
            messagebox.showerror(t("error"), t("cannot_load", e=e))


    def _render_mcw_view(self):
        if not hasattr(self, "_mcw_current_path"):
            return

        try:
            main_text, extra_text = extract_after_etx_mcw(
                self._mcw_current_path,
                exclude_hex=EXCLUDED_HEX_CODES if self.mcw_filter_control_codes.get() else None
            )
        except Exception as e:
            messagebox.showwarning(t("error"), str(e))
            return

        self.mcw_output.delete("1.0", tk.END)
        self.mcw_output.insert(tk.END, t("mcw_main"))
        self.mcw_output.insert(tk.END, main_text.strip() + "\n\n")
        if extra_text.strip():
            self.mcw_output.insert(tk.END, t("mcw_extra"))
            self.mcw_output.insert(tk.END, extra_text.strip())


    # ---------------- MCW Compare Tab (stesure) ------------------------
    def _build_mcw_compare_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=t("tab_compare"))

        ttk.Label(
            tab,
            text=t("compare_desc"),
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
            text=t("choose_mcw"),
            command=self._select_mcw_for_compare
        ).pack(side="left", padx=5)

        ttk.Button(
            tab,
            text=t("run_compare"),
            command=self._run_mcw_compare
        ).pack(pady=(0, 5))

        # PanedWindow con due Text
        pane = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        pane.pack(fill="both", expand=True, padx=5, pady=5)

        # colonna HEX
        left_frame = ttk.Frame(pane)
        ttk.Label(left_frame, text=t("first_draft_hex")).pack(anchor="w")
        self.mcw_compare_hex_text = tk.Text(
            left_frame,
            wrap="none",
            font=("Courier New", 10)
        )
        self.mcw_compare_hex_text.pack(fill="both", expand=True)
        pane.add(left_frame, weight=1)

        # colonna DEF
        right_frame = ttk.Frame(pane)
        ttk.Label(right_frame, text=t("final_draft_def")).pack(anchor="w")
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
            text=t("save_hex"),
            command=self._save_compare_hex
        ).pack(side="right", padx=5)
        ttk.Button(
            btn_frame,
            text=t("save_def"),
            command=self._save_compare_def
        ).pack(side="right", padx=5)
        ttk.Button(
            btn_frame,
            text=t("save_both"),
            command=self._save_compare_both
        ).pack(side="right", padx=5)
        ttk.Button(
            btn_frame,
            text=t("save_diff"),
            command=self._save_compare_diff_html
        ).pack(side="left", padx=5)

    def _select_mcw_for_compare(self):
        path = filedialog.askopenfilename(
            title=t("select_mcw"),
            filetypes=[(t("all_files"), "*.*")]
        )
        if path:
            self.mcw_compare_path_var.set(path)

    def _run_mcw_compare(self):
        path = self.mcw_compare_path_var.get().strip()
        if not path:
            messagebox.showwarning(t("warning"), t("select_mcw_first"))
            return

        try:
            with open(path, "rb") as f:
                data = f.read()
        except Exception as e:
            messagebox.showerror(t("error"), t("cannot_read", e=e))
            return

        try:
            prima_raw = estrai_prima_stesura_hex_da_mcw_bytes(data)
        except Exception as e:
            messagebox.showerror(t("error"), t("err_first_draft", e=e))
            return

        try:
            odt_path = converti_mcw_in_odt(path)
            finale_raw = estrai_testo_da_odt(odt_path)
        except Exception as e:
            messagebox.showerror(t("error"), t("err_final_draft", e=e))
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
            messagebox.showwarning(t("empty"), t("no_first_draft"))
            return
        out_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            title=t("save_first_title")
        )
        if not out_path:
            return
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(self._mcw_compare_prima)
        messagebox.showinfo(t("saved"), t("first_saved", path=out_path))

    def _save_compare_def(self):
        if not hasattr(self, "_mcw_compare_finale"):
            messagebox.showwarning(t("empty"), t("no_final_draft"))
            return
        out_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            title=t("save_final_title")
        )
        if not out_path:
            return
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(self._mcw_compare_finale)
        messagebox.showinfo(t("saved"), t("final_saved", path=out_path))

    def _save_compare_both(self):
        if not (hasattr(self, "_mcw_compare_prima") and hasattr(self, "_mcw_compare_finale")):
            messagebox.showwarning(t("empty"), t("no_drafts"))
            return
        base = filedialog.asksaveasfilename(
            defaultextension=".txt",
            title=t("base_name_title")
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
            t("saved"),
            t("files_saved", a=hex_path, b=def_path)
        )

    def _save_compare_diff_html(self):
        if not (hasattr(self, "_mcw_compare_prima") and hasattr(self, "_mcw_compare_finale")):
            messagebox.showwarning(t("empty"), t("no_drafts_compare"))
            return
        out_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            title=t("save_diff_title")
        )
        if not out_path:
            return

        old_lines = self._mcw_compare_prima.splitlines()
        new_lines = self._mcw_compare_finale.splitlines()

        html = difflib.HtmlDiff(wrapcolumn=80).make_file(
            old_lines,
            new_lines,
            fromdesc=t("diff_from"),
            todesc=t("diff_to"),
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        messagebox.showinfo(t("saved"), t("diff_saved", path=out_path))



#====================== TAB PER ANALISI DATE ==================#
    def _build_date_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=t("tab_dates"))

        # Titolo descrittivo
        ttk.Label(tab, text=t("dates_desc"), foreground="#444", font=("Segoe UI", 9, "italic"))\
            .pack(anchor="w", padx=5, pady=(5, 0))

        # --- Scelta directory ---
        dir_frame = ttk.Frame(tab)
        dir_frame.pack(fill="x", padx=5, pady=5)

        self.date_dir_var = tk.StringVar()
        ttk.Entry(dir_frame, textvariable=self.date_dir_var, width=80).pack(side="left", fill="x", expand=True)
        ttk.Button(dir_frame, text=t("choose_folder"), command=self._browse_date_dir).pack(side="left", padx=5)

        # --- Scelta campo data ---
        field_frame = ttk.Frame(tab)
        field_frame.pack(fill="x", padx=5)

        ttk.Label(field_frame, text=t("date_field_to_analyze")).pack(side="left")
        combo, self._date_field_code = self._make_combo(
            field_frame,
            [("Created", "field_created"), ("Modified", "field_modified"), ("Backup", "field_backup")],
            "Created", 15)
        combo.pack(side="left", padx=5)

        # --- Intervallo giorni tra Creato e Modificato ---
        range_frame = ttk.Frame(tab)
        range_frame.pack(fill="x", padx=5, pady=(0, 5))

        ttk.Label(range_frame, text=t("delta_range")).pack(side="left")
        self.delta_min = tk.IntVar(value=0)
        self.delta_max = tk.IntVar(value=90)

        min_spin = ttk.Spinbox(range_frame, from_=0, to=365, textvariable=self.delta_min, width=5)
        min_spin.pack(side="left", padx=(5, 2))
        min_spin.bind("<FocusOut>", lambda e: self._plot_deltas())
        min_spin.bind("<Return>", lambda e: self._plot_deltas())

        ttk.Label(range_frame, text=t("to")).pack(side="left")

        max_spin = ttk.Spinbox(range_frame, from_=0, to=365, textvariable=self.delta_max, width=5)
        max_spin.pack(side="left", padx=(2, 10))
        max_spin.bind("<FocusOut>", lambda e: self._plot_deltas())
        max_spin.bind("<Return>", lambda e: self._plot_deltas())



        # --- Pulsante analisi ---
        ttk.Button(tab, text=t("extract_analyze"), command=self._run_date_analysis).pack(pady=5)

        # --- Output testuale ---
        self.date_output = scrolledtext.ScrolledText(tab, wrap="word", font=("Segoe UI", 10))
        self.date_output.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Pulsanti export ---
        out_frame = ttk.Frame(tab)
        out_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(out_frame, text=t("save_csv"), command=self._save_date_csv).pack(side="right", padx=5)
        ttk.Button(out_frame, text=t("plot_annual"), command=self._plot_annual).pack(side="left", padx=5)
        ttk.Button(out_frame, text=t("plot_monthly"), command=self._plot_monthly).pack(side="left", padx=5)
        ttk.Button(out_frame, text=t("plot_deltas"), command=self._plot_deltas).pack(side="left", padx=5)

        # Placeholder per dataframe risultati
        self.date_df = None

    def _browse_date_dir(self):
        folder = filedialog.askdirectory(title=t("select_catalog_folder"))
        if folder:
            self.date_dir_var.set(folder)

    def _run_date_analysis(self):
        folder = self.date_dir_var.get()
        field = self._date_field_code()
        if not folder:
            messagebox.showwarning(t("warning"), t("select_valid_folder"))
            return

        try:
            df = estrai_date_catalog(folder)
            if df.empty:
                raise ValueError(t("no_valid_data"))
            self.date_df = df
        except Exception as e:
            messagebox.showerror(t("error"), str(e))
            return

        self.date_output.delete("1.0", tk.END)
        self.date_output.insert(tk.END, t("total_found", n=len(df)))

        try:
            serie = pd.to_datetime(df[field], errors="coerce").dropna()
            self.date_output.insert(tk.END, t("date_range", a=serie.min().date(), b=serie.max().date()))
        except:
            self.date_output.insert(tk.END, t("err_dates"))

    def _save_date_csv(self):
        import pandas as pd
        if self.date_df is None or self.date_df.empty:
            messagebox.showwarning(t("empty"), t("no_data_to_save"))
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".csv")
        if not out_path:
            return
        self.date_df.to_csv(out_path, index=False, encoding="utf-8")
        messagebox.showinfo(t("saved"), t("csv_saved", path=out_path))

    def _plot_annual(self):
        import pandas as pd
        import matplotlib.pyplot as plt
        if self.date_df is None:
            return
        field = self._date_field_code()
        serie = pd.to_datetime(self.date_df[field], errors="coerce").dropna()
        years = serie.dt.year.value_counts().sort_index()
        years.plot(kind="bar")
        plt.title(t("plot_annual_title", field=t("field_" + field.lower())))
        plt.xlabel(t("plot_year"))
        plt.ylabel(t("plot_nfiles"))
        plt.tight_layout()
        plt.show()

    def _plot_monthly(self):
        import pandas as pd
        import matplotlib.pyplot as plt
        if self.date_df is None:
            return

        field = self._date_field_code()
        serie = pd.to_datetime(self.date_df[field], errors="coerce").dropna()

        # Raggruppa per anno-mese e converte in stringa es. "2023-01"
        grouped = serie.dt.to_period("M").astype(str).value_counts().sort_index()

        # Plot
        grouped.plot(kind="bar", figsize=(10, 4))
        plt.title(t("plot_monthly_title", field=t("field_" + field.lower())))
        plt.xlabel(t("plot_month"))
        plt.ylabel(t("plot_nfiles"))
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

            serie = pd.to_datetime(self.date_df["Created"], errors="coerce")
            delta = pd.to_datetime(self.date_df["Modified"], errors="coerce") - serie
            delta_days = delta.dt.total_seconds().dropna() / 86400

            # Filtra per intervallo selezionato
            filtered = delta_days[(delta_days >= min_days) & (delta_days <= max_days)]
            if filtered.empty:
                messagebox.showinfo(t("no_results"), t("no_files_in_range"))
                return

            filtered.hist(bins=30)
            plt.title(t("plot_delta_title", a=min_days, b=max_days))
            plt.xlabel(t("plot_days"))
            plt.ylabel(t("plot_freq"))
            plt.tight_layout()
            plt.show()

        except Exception as e:
            messagebox.showwarning(t("error"), t("calc_problem", e=e))


# ------------- Utils -----------------------------
    def _open_guida_tab(self):
        # Crea tab solo se non già presente
        if hasattr(self, "_guida_tab"):
            self.notebook.select(self._guida_tab)
            return

        self._guida_tab = ttk.Frame(self.notebook)
        self.notebook.add(self._guida_tab, text=t("tab_guide"))
        self.notebook.select(self._guida_tab)

        guida_text = scrolledtext.ScrolledText(self._guida_tab, wrap="word", font=("Segoe UI", 10))
        guida_text.pack(fill="both", expand=True, padx=10, pady=10)

        guida_text.insert(tk.END, t("guide_intro"))

        # Link cliccabile a hexed.it
        start = guida_text.index(tk.INSERT)
        guida_text.insert(tk.END, "https://hexed.it\n")
        end = guida_text.index(tk.INSERT)
        guida_text.tag_add("hexed_link", start, end)
        guida_text.tag_config("hexed_link", foreground="blue", underline=True)
        guida_text.tag_bind("hexed_link", "<Button-1>", lambda e: webbrowser.open_new("https://hexed.it"))

        # Resto della guida
        guida_text.insert(tk.END, t("guide_body"))


        guida_text.configure(state="disabled")




    def _save_text_widget(self, widget: tk.Text):
        txt = widget.get("1.0", tk.END).strip()
        if not txt:
            messagebox.showwarning(t("empty"), t("nothing_to_save"))
            return
        out_path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not out_path:
            return
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(txt)
        messagebox.showinfo(t("saved"), t("file_saved_in", path=out_path))
