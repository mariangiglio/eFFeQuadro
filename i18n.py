"""
Testi dell'interfaccia in italiano e inglese.

Uso:
    from i18n import t
    t("open_catalog")                  -> testo nella lingua corrente
    t("click_to_open", name="catalog") -> testo con segnaposto riempiti

La lingua scelta viene salvata in ~/.effequadro.json.
Al primo avvio si usa la lingua del sistema (italiano se il sistema è in
italiano, altrimenti inglese).

Per aggiungere un testo: aggiungere una voce a STRINGS con entrambe le lingue.
"""

import json
import locale
from pathlib import Path

LANGUAGES = {"it": "Italiano", "en": "English"}
SETTINGS_PATH = Path.home() / ".effequadro.json"


def _detect_system_language() -> str:
    try:
        loc = locale.getlocale()[0] or ""
    except Exception:
        loc = ""
    # es. "it_IT" su Linux/macOS, "Italian_Italy" su Windows
    return "it" if loc.lower().startswith("it") else "en"


def _load_language() -> str:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            lang = json.load(f).get("language")
        if lang in LANGUAGES:
            return lang
    except Exception:
        pass
    return _detect_system_language()


_current = _load_language()


def get_language() -> str:
    return _current


def set_language(lang: str) -> None:
    """Imposta la lingua e la salva per i prossimi avvii."""
    global _current
    if lang not in LANGUAGES:
        return
    _current = lang
    try:
        settings = {}
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
        settings["language"] = lang
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except Exception:
        # se non si può salvare, la lingua vale solo per questa sessione
        pass


def t(key: str, **kwargs) -> str:
    """Restituisce il testo `key` nella lingua corrente."""
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(_current) or entry.get("en") or key
    return text.format(**kwargs) if kwargs else text


# =============================================================================
#                                   TESTI
# =============================================================================

STRINGS = {
    # ---------------- Generali ----------------
    "app_title": {"it": "eFFeQuadro - Forensic Toolkit", "en": "eFFeQuadro - Forensic Toolkit"},
    "error": {"it": "Errore", "en": "Error"},
    "warning": {"it": "Attenzione", "en": "Warning"},
    "empty": {"it": "Vuoto", "en": "Empty"},
    "saved": {"it": "Salvato", "en": "Saved"},
    "no_results": {"it": "Nessun risultato", "en": "No results"},
    "all_files": {"it": "Tutti i file", "en": "All files"},
    "click_to_open": {"it": "📂 File: {name} (clic per aprire)", "en": "📂 File: {name} (click to open)"},
    "error_prefix": {"it": "Errore: {e}", "en": "Error: {e}"},
    "err_parsing": {"it": "Errore durante il parsing:\n{e}", "en": "Error while parsing:\n{e}"},
    "err_saving": {"it": "Errore durante il salvataggio:\n{e}", "en": "Error while saving:\n{e}"},
    "save_failed": {"it": "Salvataggio fallito:\n{e}", "en": "Save failed:\n{e}"},
    "save_output": {"it": "Salva Output", "en": "Save Output"},
    "save_output_lc": {"it": "Salva output", "en": "Save output"},
    "nothing_to_save": {"it": "Nulla da salvare.", "en": "Nothing to save."},
    "no_results_to_save": {"it": "Nessun risultato da salvare.", "en": "No results to save."},
    "file_saved_in": {"it": "File salvato in {path}", "en": "File saved to {path}"},
    "output_saved_in": {"it": "Output salvato in {path}", "en": "Output saved to {path}"},
    "hide_system_chars": {"it": "Nascondi caratteri di sistema", "en": "Hide system characters"},
    "to": {"it": "a", "en": "to"},

    # ---------------- Menu ----------------
    "menu_guide": {"it": "📘 Guida", "en": "📘 Guide"},
    "menu_open_guide": {"it": "Apri Guida Utente", "en": "Open User Guide"},
    "menu_credits": {"it": "ℹ️ Credits", "en": "ℹ️ Credits"},
    "menu_about": {"it": "Informazioni sull'autore", "en": "About the author"},
    "credits_text": {
        "it": "eFFeQuadro - Forensic Toolkit\n"
              "Sviluppato da Mariangela Giglio\n"
              "Versione: 1.0.0\n"
              "GitHub: https://github.com/mariangiglio\n"
              "Licenza: MIT",
        "en": "eFFeQuadro - Forensic Toolkit\n"
              "Developed by Mariangela Giglio\n"
              "Version: 1.0.0\n"
              "GitHub: https://github.com/mariangiglio\n"
              "License: MIT",
    },
    "menu_themes": {"it": "🎨 Temi", "en": "🎨 Themes"},
    "menu_language": {"it": "🌐 Lingua / Language", "en": "🌐 Lingua / Language"},
    "lang_title": {"it": "Lingua", "en": "Language"},
    "lang_confirm": {
        "it": "Cambiando lingua l'interfaccia viene ricaricata e i risultati aperti vengono chiusi.\n\nContinuare?",
        "en": "Changing the language reloads the interface and closes any open results.\n\nContinue?",
    },

    # ---------------- Temi ----------------
    "theme_aquativo": {"it": "Aquativo (Acqua brillante)", "en": "Aquativo (Bright aqua)"},
    "theme_adapta": {"it": "Adapta (Material Design bianco celeste)", "en": "Adapta (White and light blue)"},
    "theme_black": {"it": "Black (Scuro)", "en": "Black (Dark)"},
    "theme_blue": {"it": "Blue (Chiaro)", "en": "Blue (Light)"},
    "theme_breeze": {"it": "Breeze (Grigio e celeste)", "en": "Breeze (Grey and light blue)"},
    "theme_clearlooks": {"it": "Clearlooks (Morbido)", "en": "Clearlooks (Soft)"},
    "theme_itft1": {"it": "ITFT1 (Classico IT)", "en": "ITFT1 (Classic IT)"},
    "theme_kroc": {"it": "Kroc (Arancione)", "en": "Kroc (Orange)"},
    "theme_plastik": {"it": "Plastik (Pulito KDE‑like)", "en": "Plastik (Clean, KDE‑like)"},
    "theme_radiance": {"it": "Radiance (Ubuntu Like)", "en": "Radiance (Ubuntu-like)"},
    "theme_xpnative": {"it": "XPnative (Tema classico XP)", "en": "XPnative (Classic XP theme)"},

    # ---------------- Info File ----------------
    "tab_info": {"it": "Info File", "en": "File Info"},
    "info_desc": {"it": "🔍 Analisi tipo file", "en": "🔍 File type analysis"},
    "choose_file": {"it": "Scegli File", "en": "Choose File"},
    "select_file_to_analyze": {"it": "Seleziona un file da analizzare", "en": "Select a file to analyse"},
    "sys_desktop_db": {"it": "File di sistema - Desktop DB", "en": "System file - Desktop DB"},
    "sys_desktop": {"it": "File di sistema - Desktop", "en": "System file - Desktop"},
    "sys_finder": {"it": "File di sistema - Finder.dat", "en": "System file - Finder.dat"},
    "sys_trash": {"it": "File di sistema - Cestino", "en": "System file - Trash"},
    "recognized": {"it": "📄 Riconosciuto: {label}\n", "en": "📄 Recognised: {label}\n"},
    "word5": {"it": "Word 5.0 (dal 1991)", "en": "Word 5.0 (from 1991)"},
    "word4": {"it": "Word 4.0 (dal 1989)", "en": "Word 4.0 (from 1989)"},
    "word3": {"it": "Word 3.0 (dal 1987)", "en": "Word 3.0 (from 1987)"},
    "word_recognized": {"it": "📝 Documento Word riconosciuto: {version}\n", "en": "📝 Word document recognised: {version}\n"},
    "word5_notes": {
        "it": "• Parte di Office 2 e 2.5 (1992)\n• Richiede System 6.0.2, RAM 512kB+\n",
        "en": "• Part of Office 2 and 2.5 (1992)\n• Requires System 6.0.2, 512 KB+ RAM\n",
    },
    "word51_notes": {
        "it": "• Ultima versione per CPU 68000\n• Parte di Office 3 (1993)\n• Supporta spellcheck\n",
        "en": "• Last version for 68000 CPUs\n• Part of Office 3 (1993)\n• Supports spellcheck\n",
    },
    "word6_notes": {
        "it": "• Parte di Office 4.2\n• UI condivisa con Word per Windows\n• Richiede System 7.0, 4 MB RAM\n",
        "en": "• Part of Office 4.2\n• UI shared with Word for Windows\n• Requires System 7.0, 4 MB RAM\n",
    },
    "probably_text": {"it": "✏️ Probabile file testuale\n", "en": "✏️ Probably a text file\n"},
    "type_uncertain": {"it": "❓ Tipo file non determinato con certezza\n", "en": "❓ File type could not be determined with certainty\n"},

    # ---------------- Allocation & Extents ----------------
    "tab_alloc": {"it": "HFS - Allocation & Extents", "en": "HFS - Allocation & Extents"},
    "alloc_desc": {"it": "💾 Analisi su volume HFS (floppy)", "en": "💾 HFS volume analysis (floppy)"},
    "open_alloc": {"it": "Apri Allocation", "en": "Open Allocation"},
    "open_extents": {"it": "Apri Extents Overflow", "en": "Open Extents Overflow"},
    "select_alloc": {"it": "Seleziona file Allocation (bitmap)", "en": "Select Allocation file (bitmap)"},
    "alloc_summary": {
        "it": "Blocchi totali: {total}\nBlocchi utilizzati: {used}\nBlocchi liberi: {free}\n\n",
        "en": "Total blocks: {total}\nUsed blocks: {used}\nFree blocks: {free}\n\n",
    },
    "select_extents": {"it": "Seleziona file Extents Overflow", "en": "Select Extents Overflow file"},
    "extents_none": {
        "it": "Nessun record di extent trovato.\n(Un albero Extents Overflow vuoto è normale nei volumi senza file frammentati.)\n",
        "en": "No extent records found.\n(An empty Extents Overflow tree is normal on volumes without fragmented files.)\n",
    },
    "extents_header": {
        "it": "CNID: {cnid}  Fork: {fork}  Formato: {fmt}  Blocco logico iniziale: {fblock}\n",
        "en": "CNID: {cnid}  Fork: {fork}  Format: {fmt}  First logical block: {fblock}\n",
    },
    "extent_line": {
        "it": "  Extent {i}: blocco iniziale {start}, lunghezza {count}\n",
        "en": "  Extent {i}: start block {start}, length {count}\n",
    },

    # ---------------- Catalog ----------------
    "tab_catalog": {"it": "HFS - Catalog", "en": "HFS - Catalog"},
    "catalog_desc": {
        "it": "📂 Sintesi strutturale di cartella o volume HFS con metadati",
        "en": "📂 Structural summary of an HFS folder or volume with metadata",
    },
    "open_catalog": {"it": "Apri Catalog B‑tree", "en": "Open Catalog B‑tree"},
    "search_name": {"it": "Cerca per nome:", "en": "Search by name:"},
    "filter_type": {"it": "Filtra per tipo:", "en": "Filter by type:"},
    "opt_all": {"it": "Tutti", "en": "All"},
    "rectype_file": {"it": "File", "en": "File"},
    "rectype_folder": {"it": "Cartella", "en": "Folder"},
    "rectype_folder_thread": {"it": "Thread Cartella", "en": "Folder thread"},
    "rectype_file_thread": {"it": "Thread File", "en": "File thread"},
    "rectype_unknown": {"it": "Tipo sconosciuto ({n})", "en": "Unknown type ({n})"},
    "year_from": {"it": "Anno da:", "en": "Year from:"},
    "year_to": {"it": "a:", "en": "to:"},
    "date_field": {"it": "Campo data:", "en": "Date field:"},
    "field_created": {"it": "Creato", "en": "Created"},
    "field_modified": {"it": "Modificato", "en": "Modified"},
    "field_backup": {"it": "Backup", "en": "Backup"},
    "sort_by": {"it": "Ordina per:", "en": "Sort by:"},
    "sort_name": {"it": "Nome", "en": "Name"},
    "sort_type": {"it": "Tipo", "en": "Type"},
    "sort_date": {"it": "Data", "en": "Date"},
    "sort_asc": {"it": "↑ crescente", "en": "↑ ascending"},
    "sort_desc": {"it": "↓ decrescente", "en": "↓ descending"},
    "apply_filter": {"it": "Applica filtro", "en": "Apply filter"},
    "save_filtered": {"it": "Salva Output Filtrato", "en": "Save Filtered Output"},
    "save_full_catalog": {"it": "Salva Catalog Completo", "en": "Save Full Catalog"},
    "select_catalog": {"it": "Seleziona file Catalog", "en": "Select Catalog file"},
    "catalog_entry": {
        "it": "Nome: {name}\n  Tipo: {type}\n  ParentID: {parent}\n  CNID: {cnid}\n"
              "  Creato: {created}\n  Modificato: {modified}\n  Backup: {backup}\n",
        "en": "Name: {name}\n  Type: {type}\n  ParentID: {parent}\n  CNID: {cnid}\n"
              "  Created: {created}\n  Modified: {modified}\n  Backup: {backup}\n",
    },
    "no_filtered": {"it": "Nessun risultato filtrato da salvare.", "en": "No filtered results to save."},
    "save_filtered_title": {"it": "Salva output filtrato", "en": "Save filtered output"},
    "catalog_not_loaded": {"it": "Il catalog non è stato ancora caricato.", "en": "No catalog has been loaded yet."},
    "save_full_title": {"it": "Salva catalog completo", "en": "Save full catalog"},
    "full_saved": {"it": "Catalog completo salvato in {path}", "en": "Full catalog saved to {path}"},
    "date_error": {"it": "Errore", "en": "Error"},

    # ---------------- Delete-Log ----------------
    "tab_delete": {"it": "HFS - Delete‑Log", "en": "HFS - Delete‑Log"},
    "delete_desc": {"it": "📄 Analisi su file grezzo (spazio non allocato)", "en": "📄 Raw file analysis (unallocated space)"},
    "open_delete": {"it": "Apri Delete‑Log", "en": "Open Delete‑Log"},
    "select_delete": {"it": "Seleziona file Delete Log", "en": "Select Delete Log file"},
    "delete_entry": {"it": "Offset: {off}  Tipo: {label}\n", "en": "Offset: {off}  Type: {label}\n"},
    "desc_mswdwdbn": {"it": "Microsoft Word Document", "en": "Microsoft Word Document"},
    "desc_mswdwtmp": {"it": "File temporaneo Word", "en": "Word temporary file"},

    # ---------------- MDB ----------------
    "tab_mdb": {"it": "HFS - MDB Header", "en": "HFS - MDB Header"},
    "mdb_desc": {"it": "💾 Analisi su intestazione del volume (floppy HFS)", "en": "💾 Volume header analysis (HFS floppy)"},
    "open_mdb": {"it": "Apri MDB", "en": "Open MDB"},
    "save_mdb": {"it": "Salva Output MDB", "en": "Save MDB Output"},
    "select_mdb": {"it": "Seleziona file MDB", "en": "Select MDB file"},
    "mdb_no_sig": {"it": "Firma BD non trovata né a offset 0 né 0x400", "en": "BD signature not found at offset 0 or 0x400"},
    "mdb_signature": {"it": "Firma del volume", "en": "Volume signature"},
    "mdb_created": {"it": "Data creazione", "en": "Creation date"},
    "mdb_modified": {"it": "Data modifica", "en": "Modification date"},
    "mdb_flags": {"it": "Flags volume", "en": "Volume flags"},
    "mdb_root_files": {"it": "File in root", "en": "Files in root"},
    "mdb_bitmap_block": {"it": "Blocco bitmap", "en": "Bitmap start block"},
    "mdb_next_alloc": {"it": "Next alloc", "en": "Next allocation search"},
    "mdb_alloc_blocks": {"it": "Numero blocchi alloc", "en": "Allocation blocks"},
    "mdb_alloc_size": {"it": "Dim. blocco alloc", "en": "Allocation block size"},
    "mdb_clump": {"it": "Clump default", "en": "Default clump size"},
    "mdb_first_alloc": {"it": "Primo blocco alloc", "en": "First allocation block"},
    "mdb_next_cnid": {"it": "CNID prossimo catalogo", "en": "Next catalog CNID"},
    "mdb_free_blocks": {"it": "Blocchi liberi", "en": "Free blocks"},
    "mdb_label_len": {"it": "Lunghezza etichetta", "en": "Volume name length"},
    "mdb_label": {"it": "Etichetta volume", "en": "Volume name"},
    "mdb_backup": {"it": "Data backup", "en": "Backup date"},

    # ---------------- Split Word Segments ----------------
    "tab_split": {"it": "Split Word Segments", "en": "Split Word Segments"},
    "split_desc": {"it": "📄 Analisi di file binario grezzo per segmenti Word", "en": "📄 Raw binary file analysis for Word segments"},
    "select_binary": {"it": "Seleziona file binario", "en": "Select binary file"},
    "split_hint": {
        "it": "(Dividi automaticamente in corrispondenza dei marker di file Word)",
        "en": "(Automatically split at Word file markers)",
    },
    "save_file_list": {"it": "Salva elenco file", "en": "Save file list"},
    "select_to_split": {"it": "Seleziona file da splittare", "en": "Select file to split"},
    "choose_out_dir": {"it": "Scegli dove salvare i file generati", "en": "Choose where to save the generated files"},
    "err_split": {"it": "Errore durante lo split:\n{e}", "en": "Error while splitting:\n{e}"},
    "no_segments": {"it": "Nessun segmento Word riconoscibile trovato.", "en": "No recognisable Word segments found."},
    "original_file": {"it": "📂 File originale: {name} (clic per aprire)\n", "en": "📂 Original file: {name} (click to open)\n"},
    "generated_files": {"it": "\n📄 File generati ({n}):\n\n", "en": "\n📄 Generated files ({n}):\n\n"},

    # ---------------- Hex Decoder ----------------
    "tab_hex": {"it": "UTILS - Hex → ASCII Decoder", "en": "UTILS - Hex → ASCII Decoder"},
    "hex_desc": {"it": "📄 Decodifica manuale di stringhe esadecimali", "en": "📄 Manual decoding of hexadecimal strings"},
    "hex_title": {"it": "Hex → ASCII Decoder", "en": "Hex → ASCII Decoder"},
    "hex_input": {"it": "Input esadecimale", "en": "Hexadecimal input"},
    "decoded_result": {"it": "Risultato decodificato", "en": "Decoded result"},
    "decode": {"it": "Decodifica", "en": "Decode"},

    # ---------------- MCW Hidden Text ----------------
    "tab_mcw": {"it": "Word - MCW Hidden Text", "en": "Word - MCW Hidden Text"},
    "mcw_desc": {"it": "📄 Estrazione da file Word per Mac (.mcw)", "en": "📄 Extraction from Word for Mac files (.mcw)"},
    "open_file": {"it": "Apri file", "en": "Open file"},
    "open_default_app": {"it": "📂 Apri file con programma predefinito", "en": "📂 Open file with default application"},
    "save_text": {"it": "Salva testo", "en": "Save text"},
    "select_mcw": {"it": "Seleziona file .mcw", "en": "Select .mcw file"},
    "cannot_load": {"it": "Impossibile caricare il file:\n{e}", "en": "Unable to load the file:\n{e}"},
    "mcw_main": {"it": "=== TESTO PRINCIPALE POST-ETX ===\n", "en": "=== MAIN TEXT AFTER ETX ===\n"},
    "mcw_extra": {"it": "=== TESTO EXTRA DOPO ETX ===\n", "en": "=== EXTRA TEXT AFTER ETX ===\n"},
    "mcw_no_file": {"it": "Apri prima un file .mcw.", "en": "Open a .mcw file first."},

    # ---------------- Confronto Stesure ----------------
    "tab_compare": {"it": "Word - Confronto Stesure", "en": "Word - Draft Comparison"},
    "compare_desc": {
        "it": "📝 Confronto prima stesura (HEX) / stesura finale (LibreOffice)",
        "en": "📝 First draft (HEX) / final draft (LibreOffice) comparison",
    },
    "choose_mcw": {"it": "Scegli file .mcw", "en": "Choose .mcw file"},
    "run_compare": {"it": "Genera confronto stesure", "en": "Generate draft comparison"},
    "first_draft_hex": {"it": "Prima stesura (HEX)", "en": "First draft (HEX)"},
    "final_draft_def": {"it": "Stesura finale (DEF)", "en": "Final draft (DEF)"},
    "save_hex": {"it": "Salva HEX", "en": "Save HEX"},
    "save_def": {"it": "Salva DEF", "en": "Save DEF"},
    "save_both": {"it": "Salva entrambe (HEX+DEF)", "en": "Save both (HEX+DEF)"},
    "save_diff": {"it": "Salva diff (HTML)", "en": "Save diff (HTML)"},
    "select_mcw_first": {"it": "Seleziona prima un file .mcw.", "en": "Select a .mcw file first."},
    "cannot_read": {"it": "Impossibile leggere il file:\n{e}", "en": "Unable to read the file:\n{e}"},
    "err_first_draft": {
        "it": "Errore durante estrazione prima stesura:\n{e}",
        "en": "Error while extracting the first draft:\n{e}",
    },
    "err_final_draft": {
        "it": "Errore durante estrazione stesura finale con LibreOffice:\n{e}",
        "en": "Error while extracting the final draft with LibreOffice:\n{e}",
    },
    "no_first_draft": {"it": "Nessuna prima stesura da salvare.", "en": "No first draft to save."},
    "save_first_title": {"it": "Salva prima stesura (HEX)", "en": "Save first draft (HEX)"},
    "first_saved": {"it": "Prima stesura salvata in:\n{path}", "en": "First draft saved to:\n{path}"},
    "no_final_draft": {"it": "Nessuna stesura finale da salvare.", "en": "No final draft to save."},
    "save_final_title": {"it": "Salva stesura finale (DEF)", "en": "Save final draft (DEF)"},
    "final_saved": {"it": "Stesura finale salvata in:\n{path}", "en": "Final draft saved to:\n{path}"},
    "no_drafts": {"it": "Non ci sono stesure da salvare.", "en": "There are no drafts to save."},
    "base_name_title": {
        "it": "Scegli nome base (verranno creati _HEX e _DEF)",
        "en": "Choose a base name (_HEX and _DEF files will be created)",
    },
    "files_saved": {"it": "File salvati:\n{a}\n{b}", "en": "Files saved:\n{a}\n{b}"},
    "no_drafts_compare": {"it": "Non ci sono stesure da confrontare.", "en": "There are no drafts to compare."},
    "save_diff_title": {"it": "Salva diff HTML", "en": "Save HTML diff"},
    "diff_from": {"it": "Prima stesura (HEX)", "en": "First draft (HEX)"},
    "diff_to": {"it": "Stesura finale (LibreOffice)", "en": "Final draft (LibreOffice)"},
    "diff_saved": {"it": "Diff HTML salvato in:\n{path}", "en": "HTML diff saved to:\n{path}"},

    # ---------------- Analisi Date ----------------
    "tab_dates": {"it": "HFS - Analisi Date da Catalog", "en": "HFS - Catalog Date Analysis"},
    "dates_desc": {"it": "📅 Analisi temporale da file 'catalog'", "en": "📅 Time analysis from 'catalog' files"},
    "choose_folder": {"it": "Scegli Cartella", "en": "Choose Folder"},
    "date_field_to_analyze": {"it": "Campo data da analizzare:", "en": "Date field to analyse:"},
    "delta_range": {"it": "Intervallo giorni (Creato → Modificato):", "en": "Day interval (Created → Modified):"},
    "extract_analyze": {"it": "Estrai e Analizza", "en": "Extract and Analyse"},
    "save_csv": {"it": "Salva CSV", "en": "Save CSV"},
    "plot_annual": {"it": "Grafico Annuale", "en": "Annual Chart"},
    "plot_monthly": {"it": "Grafico Mensile", "en": "Monthly Chart"},
    "plot_deltas": {"it": "Distribuzione intervalli", "en": "Interval Distribution"},
    "select_catalog_folder": {"it": "Seleziona una cartella con file catalog", "en": "Select a folder containing catalog files"},
    "select_valid_folder": {"it": "Seleziona una cartella valida.", "en": "Select a valid folder."},
    "no_valid_data": {"it": "Nessun dato valido trovato.", "en": "No valid data found."},
    "total_found": {"it": "Totale record trovati: {n}\n", "en": "Total records found: {n}\n"},
    "date_range": {"it": "Intervallo date: {a} → {b}\n", "en": "Date range: {a} → {b}\n"},
    "err_dates": {"it": "Errore durante l'analisi delle date.\n", "en": "Error while analysing the dates.\n"},
    "no_data_to_save": {"it": "Nessun dato da salvare.", "en": "No data to save."},
    "csv_saved": {"it": "CSV salvato in {path}", "en": "CSV saved to {path}"},
    "plot_annual_title": {"it": "Distribuzione per Anno ({field})", "en": "Distribution by Year ({field})"},
    "plot_year": {"it": "Anno", "en": "Year"},
    "plot_nfiles": {"it": "Numero di file", "en": "Number of files"},
    "plot_monthly_title": {"it": "Distribuzione Mensile ({field})", "en": "Monthly Distribution ({field})"},
    "plot_month": {"it": "Mese", "en": "Month"},
    "no_files_in_range": {"it": "Nessun file nell'intervallo selezionato.", "en": "No files in the selected interval."},
    "plot_delta_title": {
        "it": "Intervallo Creato→Modificato ({a}-{b} giorni)",
        "en": "Created→Modified interval ({a}-{b} days)",
    },
    "plot_days": {"it": "Giorni", "en": "Days"},
    "plot_freq": {"it": "Frequenza", "en": "Frequency"},
    "calc_problem": {"it": "Problema durante il calcolo:\n{e}", "en": "Problem during the calculation:\n{e}"},

    # ---------------- Messaggi da core.py ----------------
    "err_open_file": {"it": "Errore nell'apertura file: {e}", "en": "Error opening file: {e}"},
    "err_parsing_path": {"it": "Errore parsing {path}: {e}", "en": "Error parsing {path}: {e}"},
    "mcw_too_short": {"it": "File troppo corto o non valido", "en": "File too short or invalid"},
    "etx_not_found": {"it": "Sequenza ETX non trovata nel file", "en": "ETX sequence not found in file"},
    "mcw_no_end_offset": {
        "it": "File troppo corto per contenere l'offset di chiusura",
        "en": "File too short to contain the end-of-text offset",
    },
    "mcw_bad_end_offset": {
        "it": "Offset di chiusura sospetto ({end:#x}), dovrebbe essere > {start:#x}",
        "en": "Suspicious end-of-text offset ({end:#x}), should be > {start:#x}",
    },
    "lo_not_found": {
        "it": "Non è stato trovato LibreOffice.\nInstalla LibreOffice oppure aggiungi 'soffice' al PATH di sistema.",
        "en": "LibreOffice was not found.\nInstall LibreOffice or add 'soffice' to the system PATH.",
    },
    "lo_error": {
        "it": "Errore LibreOffice (codice {code}).\n\nSTDOUT:\n{out}\n\nSTDERR:\n{err}",
        "en": "LibreOffice error (code {code}).\n\nSTDOUT:\n{out}\n\nSTDERR:\n{err}",
    },
    "lo_no_odt": {"it": "LibreOffice non ha prodotto alcun file ODT.", "en": "LibreOffice did not produce any ODT file."},

    # ---------------- Guida ----------------
    "tab_guide": {"it": "Guida", "en": "Guide"},
    "guide_intro": {
        "it": """eFFeQuadro - Forensic Toolkit

Il programma consente analisi forensi su volumi HFS e file Word per Mac.
Ogni scheda del toolkit ha un ruolo e richiede un input specifico.

────────────────────────────────────────────────────────
🔗 Strumenti consigliati
────────────────────────────────────────────────────────
    Per visualizzare in modo preliminare il contenuto esadecimale di un file,
    puoi usare il sito web gratuito:
    """,
        "en": """eFFeQuadro - Forensic Toolkit

This program performs forensic analyses on HFS volumes and Word for Mac files.
Each tab of the toolkit has a specific role and requires a specific input.

────────────────────────────────────────────────────────
🔗 Recommended tools
────────────────────────────────────────────────────────
    For a preliminary look at the hexadecimal content of a file,
    you can use the free website:
    """,
    },
    "guide_body": {
        "it": """

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
  - Estrae parametri del file system (firma BD, date, dimensioni, etichetta volume). L'etichetta indica il nome con cui un supporto (es. floppy) è stato originariamente chiamato.
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
""",
        "en": """

────────────────────────────────────────────────────────
📂 Allocation & Extents
────────────────────────────────────────────────────────
Accepted input:
  - Allocation bitmap (e.g. a file named 'allocation')
  - Extents Overflow file (e.g. 'extents')

Where to find it:
  - Both are extracted from floppy disk images or HFS partitions.

Purpose:
  - Analyses the allocation state of the blocks and reconstructs file extents. Useful for finding free space or fragmented files.

────────────────────────────────────────────────────────
🗂️ Catalog
────────────────────────────────────────────────────────
Accepted input:
  - 'catalog' file extracted from a floppy disk or HFS medium

Where to find it:
  - First level inside a root folder.

Purpose:
  - Structured summary of the contents of a folder or an entire HFS volume.
  - Shows files, folders and threads with metadata: name, CNID, ParentID, creation/modification/backup dates.
  - Supports filtering, sorting and saving the output.

────────────────────────────────────────────────────────
🧹 Delete-Log
────────────────────────────────────────────────────────
Accepted input:
  - File named 'delete-log'.

Where to find it:
  - Second level inside a root folder. Not always present.

Purpose:
  - Locates fragments of deleted Word files by scanning in blocks (256 bytes).
  - Highlights Word headers (MSWDWDBN, MSWDWTMP) and residual ASCII strings.

────────────────────────────────────────────────────────
📑 MDB Header
────────────────────────────────────────────────────────
Accepted input:
  - 'mdb' or 'mdb backup' files.

Where to find it:
  - First level inside a root folder.

Purpose:
  - Extracts file system parameters (BD signature, dates, sizes, volume name). The volume name is the name originally given to the medium (e.g. a floppy disk).
  - Useful for dating the volume and identifying the provenance or logical state of the floppy disk.

────────────────────────────────────────────────────────
✂️ Split Word Segments
────────────────────────────────────────────────────────
Accepted input:
  - Raw binary file from unallocated space, usually named with 4 digits (e.g. 1794)

Where to find it:
  - Inside the [unallocated space] folder

Purpose:
  - Automatically splits Word segments separated by specific markers.
  - Each segment is saved as a numbered .odt file.

────────────────────────────────────────────────────────
🧮 Hex → ASCII Decoder
────────────────────────────────────────────────────────
Accepted input:
  - Hexadecimal strings entered manually

Where to find it:
  - Copied from other tools (e.g. a hex editor) or from raw output.

Purpose:
  - Hexadecimal decoding using a custom Word/Mac map.
  - Useful for testing isolated blocks of text or mapping symbols.

────────────────────────────────────────────────────────
📜 MCW Hidden Text
────────────────────────────────────────────────────────
Accepted input:
  - Microsoft Word for Macintosh text files

Where to find it:
  - Any text file inside the folders/floppy disks.

Purpose:
  - Extracts hidden text beyond the main text area (after ETX).
  - Option to hide control characters and show only useful text.
""",
    },
}
