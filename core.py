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
from i18n import t


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
        print(t("err_open_file", e=e))


# ------------- PARSER UTILS  --------------------------------------------------

def hfs_timestamp_to_datetime(hfs_ts: int) -> str:
    """Convert Macintosh HFS timestamp (seconds from 1904‑01‑01) to ISO string."""
    if hfs_ts == 0:
        return "N/A"
    try:
        return (datetime(1904, 1, 1) + timedelta(seconds=hfs_ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return t("date_error")

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
    Legge un file Extents Overflow (B-tree) di un volume HFS o HFS+.

    Formato e dimensione dei nodi vengono letti dal nodo di intestazione
    (nodo 0): maxKeyLength = 7 -> HFS, maxKeyLength = 10 -> HFS+.
    Se l'intestazione non è leggibile (es. file parziale), si assume HFS
    con nodi da 512 byte.

    Vengono letti tutti i nodi foglia (tipo 0xFF = -1), compresi quelli
    non più collegati all'albero, che possono conservare record residui.

    Restituisce una lista di dizionari con:
        CNID       - ID del file (catalog node ID)
        Fork       - "Data" o "Resource"
        FileBlock  - primo blocco del fork coperto da questo record
        Extents    - lista di (blocco iniziale, numero di blocchi)
        Format     - "HFS" o "HFS+"
    """
    with open(file_path, "rb") as f:
        data = f.read()

    # ---- nodo di intestazione: dimensione nodi e formato ----
    node_size = 512
    fmt = "HFS"
    if len(data) >= 36 and data[8] == 0x01:  # 0x01 = header node
        ns = struct.unpack(">H", data[32:34])[0]
        max_key = struct.unpack(">H", data[34:36])[0]
        if ns in (512, 1024, 2048, 4096, 8192, 16384, 32768):
            node_size = ns
        if max_key == 10:
            fmt = "HFS+"
        elif max_key != 7:
            # chiave non standard: deduci il formato dalla dimensione dei nodi
            fmt = "HFS+" if node_size > 512 else "HFS"

    results = []
    for offset in range(0, len(data) - node_size + 1, node_size):
        node = data[offset : offset + node_size]
        if node[8] != 0xFF:  # solo nodi foglia (kind = -1)
            continue
        num_rec = struct.unpack(">H", node[10:12])[0]
        if num_rec == 0 or 14 + num_rec * 2 > node_size:
            continue

        for i in range(num_rec):
            rec_off = struct.unpack(">H", node[node_size - 2 * (i + 1) : node_size - 2 * i])[0]
            if rec_off < 14 or rec_off >= node_size - 2 * num_rec:
                continue
            try:
                if fmt == "HFS":
                    # chiave: keyLen(1)=7, forkType(1), fileID(4), startBlock(2)
                    key_len = node[rec_off]
                    if key_len != 7:
                        continue
                    fork_type = node[rec_off + 1]
                    cnid = struct.unpack(">I", node[rec_off + 2 : rec_off + 6])[0]
                    file_block = struct.unpack(">H", node[rec_off + 6 : rec_off + 8])[0]
                    base = rec_off + 1 + key_len
                    if base % 2:  # i record iniziano a offset pari
                        base += 1
                    # record: 3 extent da (startBlock u16, blockCount u16)
                    n_ext, fmt_ext, ext_size = 3, ">HH", 4
                else:
                    # chiave: keyLength(2)=10, forkType(1), pad(1), fileID(4), startBlock(4)
                    key_len = struct.unpack(">H", node[rec_off : rec_off + 2])[0]
                    if key_len != 10:
                        continue
                    fork_type = node[rec_off + 2]
                    cnid = struct.unpack(">I", node[rec_off + 4 : rec_off + 8])[0]
                    file_block = struct.unpack(">I", node[rec_off + 8 : rec_off + 12])[0]
                    base = rec_off + 2 + key_len
                    # record: 8 extent da (startBlock u32, blockCount u32)
                    n_ext, fmt_ext, ext_size = 8, ">II", 8

                if base + n_ext * ext_size > node_size:
                    continue

                extents = []
                for j in range(n_ext):
                    s, c = struct.unpack(fmt_ext, node[base + j * ext_size : base + (j + 1) * ext_size])
                    if c == 0:
                        break
                    extents.append((s, c))

                if extents:
                    results.append({
                        "CNID": cnid,
                        "Fork": "Data" if fork_type == 0x00 else "Resource" if fork_type == 0xFF else f"Unknown ({fork_type:#04x})",
                        "FileBlock": file_block,
                        "Extents": extents,
                        "Format": fmt,
                    })
            except (struct.error, IndexError):
                continue

    return results


# ---------- CATALOG PARSER ---------------------------------------------------

# Tipi di record del Catalog HFS -> codice interno (indipendente dalla lingua)
RECORD_TYPES = {
    1: "folder",
    2: "file",
    3: "folder_thread",
    4: "file_thread",
}


def record_type_label(entry: dict) -> str:
    """Etichetta tradotta del tipo di record di una voce del Catalog."""
    code = entry.get("Type", "unknown")
    if code == "unknown":
        return t("rectype_unknown", n=entry.get("TypeCode", "?"))
    return t("rectype_" + code)


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
                # codice interno fisso; l'etichetta tradotta si ottiene con
                # record_type_label(entry) al momento della visualizzazione
                record_type = RECORD_TYPES.get(cdr_type, "unknown")

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
                    "Name": name,
                    "Type": record_type,
                    "TypeCode": cdr_type,
                    "ParentID": par_id,
                    "CNID": cnid,
                    "Created": cr_date,
                    "Modified": md_date,
                    "Backup": bk_date
                })
            except:
                continue

    return results


# ---------- DELETE‑LOG PARSER ------------------------------------------------

def extract_ascii_strings(data: bytes, min_len: int = 4):
    return [m.decode("ascii", errors="ignore") for m in re.findall(rb"[ -~]{" + str(min_len).encode() + rb",}", data)]

# codice di tipo -> chiave del testo descrittivo (vedi i18n.py)
type_descriptions = {
    "MSWDWDBN": "desc_mswdwdbn",
    "MSWDWTMP": "desc_mswdwtmp",
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
        raise ValueError(t("mdb_no_sig"))
    data = raw[offset : offset + 162]
    def U16(b, s):
        return struct.unpack(">H", b[s : s + 2])[0]
    def U32(b, s):
        return struct.unpack(">I", b[s : s + 4])[0]
    fields = [
        (t("mdb_signature"), data[0:2].decode("ascii", "replace")),
        (t("mdb_created"), hfs_timestamp_to_datetime(U32(data, 2))),
        (t("mdb_modified"), hfs_timestamp_to_datetime(U32(data, 6))),
        (t("mdb_flags"), U16(data, 10)),
        (t("mdb_root_files"), U16(data, 12)),
        (t("mdb_bitmap_block"), U16(data, 14)),
        (t("mdb_next_alloc"), U16(data, 16)),
        (t("mdb_alloc_blocks"), U16(data, 18)),
        (t("mdb_alloc_size"), U32(data, 20)),
        (t("mdb_clump"), U32(data, 24)),
        (t("mdb_first_alloc"), U16(data, 28)),
        (t("mdb_next_cnid"), U32(data, 30)),
        (t("mdb_free_blocks"), U16(data, 34)),
        (t("mdb_label_len"), data[36]),
        (t("mdb_label"), data[37:64].decode("ascii", "replace").strip()),
        (t("mdb_backup"), hfs_timestamp_to_datetime(U32(data, 64))),
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
        raise ValueError(t("mcw_too_short"))

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
        raise ValueError(t("etx_not_found"))

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
        raise ValueError(t("mcw_no_end_offset"))

    end_offset = int.from_bytes(
        data[HEADER_END_OFFSET_POS[0]:HEADER_END_OFFSET_POS[1]],
        byteorder="big"
    )

    if end_offset <= TEXT_START_OFFSET:
        raise ValueError(t("mcw_bad_end_offset", end=end_offset, start=TEXT_START_OFFSET))

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
    raise FileNotFoundError(t("lo_not_found"))


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
        raise RuntimeError(t("lo_error", code=result.returncode, out=result.stdout, err=result.stderr))

    odt_path = outdir / (Path(mcw_path).stem + ".odt")
    if not odt_path.exists():
        # fallback: primo .odt nella cartella
        odts = list(outdir.glob("*.odt"))
        if not odts:
            raise FileNotFoundError(t("lo_no_odt"))
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
                            "Name": rec.get("Name", ""),
                            "Created": rec.get("Created", ""),
                            "Modified": rec.get("Modified", ""),
                            "Backup": rec.get("Backup", ""),
                            "Path": path
                        })
                except Exception as e:
                    print(t("err_parsing_path", path=path, e=e))
                    continue

    return pd.DataFrame(risultati)
