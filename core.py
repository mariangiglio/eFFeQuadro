import os
import re
import struct
import platform
import subprocess
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import xml.etree.ElementTree as ET
from hexmap import EXCLUDED_HEX_CODES, decode_custom_hex


#======= FUNZIONE PER APRIRE FILE CON PROGRAMMA PREDEFINITO ==============================#
def open_with_default_app(path):
    try:
        if platform.system() == "Darwin":  # macOS
            subprocess.call(("open", path))
        elif platform.system() == "Windows":
            os.startfile(path)
        else:  # Linux e altri
            subprocess.call(("xdg-open", path))
    except Exception as e:
        print(f"Errore nell'apertura file: {e}")


# ------------- PARSER UTILS  --------------------------------------------------

def hfs_timestamp_to_datetime(hfs_ts: int) -> str:
    """Convert Macintosh HFS timestamp (seconds from 1904‑01‑01) to ISO string."""
    if hfs_ts == 0:
        return "N/A"
    try:
        return (datetime(1904, 1, 1) + timedelta(seconds=hfs_ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "Errore"

# ---------- ALLOCATION / EXTENTS --------------------------------------------

def parse_allocation_bitmap(file_path: str):
    with open(file_path, "rb") as f:
        data = f.read()
    bits = "".join(f"{b:08b}" for b in data)
    used = bits.count("1")
    free = bits.count("0")
    return used, free, len(bits)


def parse_extents_overflow(file_path: str):
    """
    Prova a leggere un file Extents Overflow sia come HFS+ (32 bit) che HFS (16 bit).
    Restituisce una lista di dizionari con CNID, tipo fork e lista di extent.
    """
    def try_hfsplus(data):
        results = []
        node_size = 512
        for offset in range(0, len(data), node_size):
            node = data[offset : offset + node_size]
            if node[8] != 0x00:  # leaf node HFS+
                continue
            num_rec = struct.unpack(">H", node[10:12])[0]
            for i in range(num_rec):
                rec_off = struct.unpack(">H", node[node_size - 2 * (i + 1): node_size - 2 * i])[0]
                try:
                    key_len = struct.unpack(">H", node[rec_off:rec_off + 2])[0]
                    fork_type = node[rec_off + 2]
                    cnid = struct.unpack(">I", node[rec_off + 4 : rec_off + 8])[0]
                    base = rec_off + 2 + key_len
                    extents = []
                    for j in range(8):
                        s = struct.unpack(">I", node[base + j*8 : base + j*8 + 4])[0]
                        c = struct.unpack(">I", node[base + j*8 + 4 : base + j*8 + 8])[0]
                        if c == 0:
                            break
                        extents.append((s, c))
                    if extents:
                        results.append({
                            "CNID": cnid,
                            "Fork": "Data" if fork_type == 0 else "Resource",
                            "Extents": extents
                        })
                except Exception:
                    continue
        return results

    def try_hfs(data):
        results = []
        node_size = 512
        for offset in range(0, len(data), node_size):
            node = data[offset : offset + node_size]
            if node[8] != 0xFF:  # leaf node HFS
                continue
            num_rec = struct.unpack(">H", node[10:12])[0]
            for i in range(num_rec):
                rec_off = struct.unpack(">H", node[node_size - 2 * (i + 1): node_size - 2 * i])[0]
                try:
                    key_len = node[rec_off]
                    fork_type = node[rec_off + 1]
                    cnid = struct.unpack(">I", node[rec_off + 2 : rec_off + 6])[0]
                    aligned_len = key_len if key_len % 2 == 0 else key_len + 1
                    base = rec_off + 1 + aligned_len
                    extents = []
                    for j in range(3):
                        s = struct.unpack(">H", node[base + j*4 : base + j*4 + 2])[0]
                        c = struct.unpack(">H", node[base + j*4 + 2 : base + j*4 + 4])[0]
                        if c:
                            extents.append((s, c))
                    if extents:
                        results.append({
                            "CNID": cnid,
                            "Fork": "Data" if fork_type == 0 else "Resource",
                            "Extents": extents
                        })
                except Exception:
                    continue
        return results

    # ---- carica i dati e prova in entrambi i modi: hfs e hfs+ ----
    with open(file_path, "rb") as f:
        data = f.read()

    results_plus = try_hfsplus(data)
    if results_plus:
        return results_plus

    results_hfs = try_hfs(data)
    return results_hfs



# ---------- CATALOG PARSER ---------------------------------------------------

def parse_catalog_btree(file_path: str):
    results = []
    NODE_SIZE = 512
    with open(file_path, "rb") as f:
        data = f.read()

    for offset in range(0, len(data), NODE_SIZE):
        block = data[offset:offset + NODE_SIZE]
        if len(block) < 14:
            continue

        kind = block[8]
        if kind != 255:  # solo nodi foglia HFS classico
            continue

        num_records = struct.unpack(">H", block[10:12])[0]
        for i in range(num_records):
            rec_off = struct.unpack(">H", block[NODE_SIZE - ((i + 1) * 2):NODE_SIZE - (i * 2)])[0]
            try:
                key_len = block[rec_off]
                if key_len == 0 or rec_off + key_len >= NODE_SIZE:
                    continue

                par_id = struct.unpack(">I", block[rec_off + 2:rec_off + 6])[0]
                name_len = block[rec_off + 6]
                name_raw = block[rec_off + 7:rec_off + 7 + name_len]
                name = name_raw.decode('mac_roman', errors='replace')

                key_total_len = 1 + key_len
                if key_total_len % 2 != 0:
                    key_total_len += 1

                record_start = rec_off + key_total_len
                if record_start + 2 > NODE_SIZE:
                    continue

                cdr_type = block[record_start]
                record_type_label = {
                    1: "Cartella",
                    2: "File",
                    3: "Thread Cartella",
                    4: "Thread File"
                }.get(cdr_type, f"Tipo sconosciuto ({cdr_type})")

                cnid = "-"
                cr_date = "-"
                md_date = "-"
                bk_date = "-"

                if cdr_type == 1:  # Directory record
                    cnid = struct.unpack(">I", block[record_start + 6:record_start + 10])[0]
                    cr_date = hfs_timestamp_to_datetime(struct.unpack(">I", block[record_start + 10:record_start + 14])[0])
                    md_date = hfs_timestamp_to_datetime(struct.unpack(">I", block[record_start + 14:record_start + 18])[0])
                    bk_date = hfs_timestamp_to_datetime(struct.unpack(">I", block[record_start + 18:record_start + 22])[0])

                elif cdr_type == 2:  # File record
                    cnid = struct.unpack(">I", block[record_start + 20:record_start + 24])[0]
                    cr_date = hfs_timestamp_to_datetime(struct.unpack(">I", block[record_start + 44:record_start + 48])[0])
                    md_date = hfs_timestamp_to_datetime(struct.unpack(">I", block[record_start + 48:record_start + 52])[0])
                    bk_date = hfs_timestamp_to_datetime(struct.unpack(">I", block[record_start + 52:record_start + 56])[0])

                results.append({
                    "Nome": name,
                    "Tipo": record_type_label,
                    "ParentID": par_id,
                    "CNID": cnid,
                    "Creato": cr_date,
                    "Modificato": md_date,
                    "Backup": bk_date
                })
            except:
                continue

    return results


# ---------- DELETE‑LOG PARSER ------------------------------------------------

def extract_ascii_strings(data: bytes, min_len: int = 4):
    return [m.decode("ascii", errors="ignore") for m in re.findall(rb"[ -~]{" + str(min_len).encode() + rb",}", data)]

type_descriptions = {
    "MSWDWDBN": "Microsoft Word Document",
    "MSWDWTMP": "File temporaneo Word",
}

def parse_delete_log(file_path: str):
    results = []
    with open(file_path, "rb") as f:
        data = f.read()
    for off in range(0, len(data), 256):
        block = data[off : off + 256]
        type_code = block[0:8].decode("ascii", errors="ignore").strip()
        strings = extract_ascii_strings(block[8:])
        if strings:
            results.append((f"0x{off:06X}", type_code, strings))
    return results

# ---------- MDB PARSER -------------------------------------------------------

def parse_mdb(file_path: str):
    summary_lines = []
    fields = []
    with open(file_path, "rb") as f:
        raw = f.read(2048)
    offset = 0 if raw[0:2] == b"BD" else 1024 if raw[1024:1026] == b"BD" else None
    if offset is None:
        raise ValueError("Firma BD non trovata né a offset 0 né 0x400")
    data = raw[offset : offset + 162]
    def U16(b, s):
        return struct.unpack(">H", b[s : s + 2])[0]
    def U32(b, s):
        return struct.unpack(">I", b[s : s + 4])[0]
    fields = [
        ("Firma del volume", data[0:2].decode("ascii", "replace")),
        ("Data creazione", hfs_timestamp_to_datetime(U32(data, 2))),
        ("Data modifica", hfs_timestamp_to_datetime(U32(data, 6))),
        ("Flags volume", U16(data, 10)),
        ("File in root", U16(data, 12)),
        ("Blocco bitmap", U16(data, 14)),
        ("Next alloc", U16(data, 16)),
        ("Numero blocchi alloc", U16(data, 18)),
        ("Dim. blocco alloc", U32(data, 20)),
        ("Clump default", U32(data, 24)),
        ("Blocco ext overflow", U16(data, 28)),
        ("CNID prossimo catalogo", U32(data, 30)),
        ("Blocchi liberi", U16(data, 34)),
        ("Lunghezza etichetta", data[36]),
        ("Etichetta volume", data[37:64].decode("ascii", "replace").strip()),
        ("Data backup", hfs_timestamp_to_datetime(U32(data, 64))),
    ]
    summary = "================ MDB SUMMARY ================\n\n"
    for name, value in fields:
        summary += f"{name:<28} : {value}\n"
    return summary

# ---------- WORD SPLITTER FROM BlOCK OF TEXT ----------------------------------------------------

def split_file_on_marker(in_path: str, markers: list[bytes] = [b"\xFE\x37", b"\xFE\x34"], out_prefix: str = "segment", out_dir: str = None):
    import os
    with open(in_path, "rb") as f:
        data = f.read()

    positions = []
    for m in markers:
        pos = 0
        while True:
            i = data.find(m, pos)
            if i == -1:
                break
            positions.append((i, m))
            pos = i + 1

    if not positions:
        return []

    positions.sort(key=lambda x: x[0])

    segments = []
    for i in range(len(positions)):
        start = positions[i][0]
        end = positions[i + 1][0] if i + 1 < len(positions) else len(data)
        segments.append(data[start:end])

    if out_dir is None:
        out_dir = os.path.dirname(in_path)
    os.makedirs(out_dir, exist_ok=True)

    out_files = []
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    for idx, seg in enumerate(segments, 1):
        out_name = os.path.join(out_dir, f"{base_name}_{out_prefix}_{idx}.odt")
        with open(out_name, "wb") as fo:
            fo.write(seg)
        out_files.append(out_name)

    return out_files


#------------- Testo post ETX --------------#
ETX_MARKERS = [b"\x78\x02", b"\x75\x01\x78", b"\x02\x075\x00", b"\x75\x00", b"\x75\x00\x78"]

def extract_after_etx_mcw(path: str, exclude_hex: set = None):
    """
    Restituisce:
        main_text = testo leggibile principale post-ETX
        post_text = eventuali residui testuali dopo il blocco principale
    """
    with open(path, "rb") as f:
        content = f.read()

    if len(content) <= 0xF0:
        raise ValueError("File troppo corto o non valido")

    data = content[0xF0:]
    marker_idx = -1
    marker_len = 0

    # Trova uno dei possibili marker ETX
    for m in ETX_MARKERS:
        idx = data.find(m)
        if idx != -1:
            marker_idx = idx
            marker_len = len(m)
            break

    if marker_idx == -1:
        raise ValueError("Sequenza ETX non trovata nel file")

    # Testo dopo ETX
    after = data[marker_idx + marker_len:]
    decoded = decode_custom_hex(after.hex(), exclude_hex=exclude_hex)

    # Separazione: prima parte = testo leggibile, seconda = residui
    righe = decoded.splitlines()
    main_lines = []
    extra_lines = []
    in_extra = False

    for r in righe:
        has_alpha = any(c.isalpha() for c in r)

        if not in_extra:
            if has_alpha:
                main_lines.append(r)
            else:
                # appena il flusso smette di essere testo → inizia extra
                in_extra = True
                if r.strip():
                    extra_lines.append(r)
        else:
            if r.strip():
                extra_lines.append(r)

    return "\n".join(main_lines), "\n".join(extra_lines)


# ---------------- MCW: prima stesura + ODT / LibreOffice helpers ---------------- #

HEADER_END_OFFSET_POS = (0x1A, 0x1C)  # byte 0x1A–0x1B (slice esclusivo 0x1C)
TEXT_START_OFFSET = 0x100             # inizio area testo nel file MCW


def decode_mcw_bytes(raw_bytes: bytes, exclude_hex: set | None = EXCLUDED_HEX_CODES) -> str:
    """
    Usa la stessa logica di decode_custom_hex ma partendo direttamente dai byte MCW.
    """
    hex_string = raw_bytes.hex()
    return decode_custom_hex(hex_string, exclude_hex=exclude_hex)


def estrai_prima_stesura_hex_da_mcw_bytes(data: bytes) -> str:
    """
    Prima stesura = da 0x100 a NN, dove NN è l'offset di chiusura
    memorizzato a 0x1A–0x1B (big-endian).
    """
    if len(data) < HEADER_END_OFFSET_POS[1]:
        raise ValueError("File troppo corto per contenere l'offset di chiusura")

    end_offset = int.from_bytes(
        data[HEADER_END_OFFSET_POS[0]:HEADER_END_OFFSET_POS[1]],
        byteorder="big"
    )

    if end_offset <= TEXT_START_OFFSET:
        raise ValueError(
            f"Offset di chiusura sospetto ({end_offset:#x}), "
            f"dovrebbe essere > {TEXT_START_OFFSET:#x}"
        )

    if end_offset > len(data):
        # se l'offset è oltre la fine, fai fallback alla lunghezza reale
        end_offset = len(data)

    text_bytes = data[TEXT_START_OFFSET:end_offset]
    return decode_mcw_bytes(text_bytes)


def trova_soffice_path() -> str:
    """
    Trova un eseguibile LibreOffice (soffice).
    Prova percorso standard Windows e 'soffice' nel PATH.
    """
    candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "soffice",  # se è nel PATH
    ]
    for c in candidates:
        if c == "soffice":
            return c  # ci affidiamo al PATH
        if os.path.exists(c):
            return c
    raise FileNotFoundError(
        "Non è stato trovato LibreOffice.\n"
        "Installa LibreOffice oppure aggiungi 'soffice' al PATH di sistema."
    )


def converti_mcw_in_odt(mcw_path: str) -> str:
    """
    Usa LibreOffice headless per convertire il file MCW in ODT.
    Ritorna il percorso del file .odt in una cartella temporanea.
    """
    soffice = trova_soffice_path()

    tmpdir = tempfile.mkdtemp(prefix="mcw2odt_")
    outdir = Path(tmpdir)

    cmd = [
        soffice,
        "--headless",
        "--convert-to", "odt",
        mcw_path,
        "--outdir", str(outdir),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Errore LibreOffice (codice {result.returncode}).\n\n"
            f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        )

    odt_path = outdir / (Path(mcw_path).stem + ".odt")
    if not odt_path.exists():
        # fallback: primo .odt nella cartella
        odts = list(outdir.glob("*.odt"))
        if not odts:
            raise FileNotFoundError("LibreOffice non ha prodotto alcun file ODT.")
        odt_path = odts[0]

    return str(odt_path)


def estrai_testo_da_odt(odt_path: str) -> str:
    """
    Estrae il testo da un ODT leggendo content.xml e concatenando paragrafi/titoli.
    Simula abbastanza bene il contenuto che otterresti con copia/incolla da LibreOffice.
    """
    with zipfile.ZipFile(odt_path, "r") as zf:
        content_xml = zf.read("content.xml")

    root = ET.fromstring(content_xml)

    ns = {
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    }

    paragraphs = []
    for elem in root.iter():
        if elem.tag in (
            f"{{{ns['text']}}}p",
            f"{{{ns['text']}}}h",
        ):
            text = "".join(elem.itertext())
            paragraphs.append(text)

    return "\n".join(paragraphs)


def normalizza_rimuovi_righe_vuote(text: str) -> str:
    """
    Rimuove le righe vuote o solo spazi.
    Serve per evitare falsi positivi nei diff riga-per-riga.
    """
    righe = text.splitlines()
    righe_piene = [r for r in righe if r.strip() != ""]
    return "\n".join(righe_piene)

def normalizza_per_diff(riga: str) -> str:
    """
    Normalizza una riga per il confronto diff:
    - tab → spazio
    - spazi multipli → uno solo
    - rimuove spazi iniziali/finali
    """
    r = riga.replace("\t", " ")
    r = " ".join(r.split())
    return r.strip()

#----------------------Analisi date ----------------------------------------#
def estrai_date_catalog(directory):
    risultati = []

    for root, _, files in os.walk(directory):
        for name in files:
            if name.lower() == "catalog":
                path = os.path.join(root, name)
                try:
                    records = parse_catalog_btree(path)
                    for rec in records:
                        risultati.append({
                            "Nome": rec.get("Nome", ""),
                            "Creato": rec.get("Creato", ""),
                            "Modificato": rec.get("Modificato", ""),
                            "Backup": rec.get("Backup", ""),
                            "Percorso": path
                        })
                except Exception as e:
                    print(f"Errore parsing {path}: {e}")
                    continue

    return pd.DataFrame(risultati)
