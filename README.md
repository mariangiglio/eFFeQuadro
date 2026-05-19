# eFFe Quadro — Forensic Toolkit

Strumento di analisi forense su volumi HFS e documenti Word per Macintosh classico (anni '80–'90).

Sviluppato per supportare attività di ricerca e analisi documentale su supporti storici (floppy disk, immagini disco HFS).

---

## Funzionalità

### File System HFS

| Scheda | Descrizione |
|---|---|
| **Info File** | Riconosce il tipo di file tramite magic bytes e nome (Word, MDB, Catalog, ecc.) |
| **Allocation & Extents** | Analizza la bitmap di allocazione e il file Extents Overflow; mostra blocchi liberi/usati e frammenti |
| **Catalog** | Legge il B-tree del Catalog HFS; filtra per nome, tipo, anno e campo data; esporta in testo |
| **MDB Header** | Estrae i metadati del Master Directory Block (firma, date, etichetta volume, blocchi) |
| **Delete-Log** | Scansiona lo spazio non allocato alla ricerca di frammenti Word cancellati |
| **Analisi Date** | Estrae e visualizza graficamente le date (creazione, modifica, backup) da uno o più file Catalog |

### Documenti Word per Mac (.mcw)

| Scheda | Descrizione |
|---|---|
| **MCW Hidden Text** | Estrae il testo nascosto post-ETX dai file `.mcw` con decodifica custom Mac Roman |
| **Confronto Stesure** | Confronta la prima stesura (decodifica HEX) con la versione finale (via LibreOffice); evidenzia le differenze riga per riga e genera diff HTML |
| **Split Word Segments** | Divide un file binario grezzo in segmenti Word separati dai marker `0xFE37` / `0xFE34` |

### Strumenti

| Scheda | Descrizione |
|---|---|
| **Hex → ASCII Decoder** | Decodifica manuale di stringhe esadecimali con mappa custom Mac Roman/Word |

---

## Requisiti

### Python

Versione minima: **Python 3.10**

Installa le dipendenze con:

```bash
pip install -r requirements.txt
```

Contenuto di `requirements.txt`:

```
ttkthemes
pandas
matplotlib
```

> **Nota per Linux:** `tkinter` non è incluso nella stdlib di default su alcune distribuzioni.
> Installalo con:
> ```bash
> sudo apt install python3-tk   # Debian/Ubuntu
> sudo dnf install python3-tkinter  # Fedora
> ```

### LibreOffice

La funzione **Confronto Stesure** richiede LibreOffice installato sul sistema.

| Sistema | Download |
|---|---|
| Windows | [libreoffice.org](https://www.libreoffice.org/download/download/) |
| macOS | [libreoffice.org](https://www.libreoffice.org/download/download/) |
| Linux | `sudo apt install libreoffice` |

Su Windows, `soffice.exe` deve trovarsi in `C:\Program Files\LibreOffice\program\` oppure essere disponibile nel `PATH` di sistema.

---

## Installazione e avvio

```bash
git clone https://github.com/mariangiglio/effe-quadro.git
cd effe-quadro
pip install -r requirements.txt
python main.py
```

---

## Struttura del progetto

```
effe-quadro/
├── main.py          # Entry point — avvia la GUI
├── gui.py           # Interfaccia grafica (tkinter + ttkthemes)
├── core.py          # Funzioni di parsing e analisi (HFS, MCW, MDB…)
├── hexmap.py        # Mappa esadecimale custom Mac Roman + funzione di decodifica
├── logo.ico         # Icona applicazione (opzionale)
├── requirements.txt
└── README.md
```

---

## Input supportati

I file di input sono tipicamente estratti da immagini di floppy disk HFS tramite strumenti come [HFSExplorer](https://www.catacombae.org/hfsexplorer/) o FTK Imager.

| File | Dove si trova nel volume HFS |
|---|---|
| `catalog` | Root del volume |
| `mdb` / `mdb backup` | Root del volume |
| `extents` | Root del volume |
| `allocation` | Root del volume |
| `delete-log` | Secondo livello, non sempre presente |
| `*.mcw` | Cartelle utente nel volume |
| File binario grezzo (es. `1794`) | Cartella `[unallocated space]` |

---

## Strumenti consigliati in abbinamento

- [hexed.it](https://hexed.it) — visualizzatore esadecimale online per ispezione preliminare
- [HFSExplorer](https://www.catacombae.org/hfsexplorer/) — estrazione file da immagini HFS
- LibreOffice — conversione e lettura file `.mcw`

---

## Temi grafici

L'interfaccia supporta più temi visivi selezionabili dal menu **🎨 Temi**:
`aquativo`, `adapta`, `black`, `blue`, `breeze`, `clearlooks`, `itft1`, `kroc`, `plastik`, `radiance`, `xpnative`.

---

## Autore

**Mariangela Giglio**
GitHub: [github.com/mariangiglio](https://github.com/mariangiglio)

---

## Licenza

Questo software è distribuito per uso interno e didattico.
Ogni altro utilizzo richiede autorizzazione esplicita dell'autore.
