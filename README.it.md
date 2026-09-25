# eFFeQuadro — Forensic Toolkit

[English](README.md) · **Italiano**

Strumento di analisi forense su volumi HFS e documenti Word per Macintosh classico (anni '80–'90).

Sviluppato per supportare attività di ricerca e analisi documentale su supporti storici (floppy disk, immagini disco HFS).

L'interfaccia è disponibile in **italiano e inglese**: la lingua si cambia dal menu **🌐 Lingua / Language** e la scelta viene ricordata alla sessione successiva.

---

## Funzionalità

### File System HFS

| Scheda | Descrizione |
|---|---|
| **Info File** | Riconosce il tipo di file tramite magic bytes e nome (Word, MDB, Catalog, ecc.) |
| **HFS - Allocation & Extents** | Analizza la bitmap di allocazione e il file Extents Overflow (HFS e HFS+); mostra blocchi liberi/usati e gli extent dei file frammentati |
| **HFS - Catalog** | Legge il B-tree del Catalog HFS; filtra per nome, tipo, anno e campo data; esporta in testo |
| **HFS - MDB Header** | Estrae i metadati del Master Directory Block (firma, date, etichetta volume, blocchi) |
| **HFS - Delete-Log** | Scansiona lo spazio non allocato alla ricerca di frammenti Word cancellati |
| **HFS - Analisi Date da Catalog** | Estrae e visualizza graficamente le date (creazione, modifica, backup) da uno o più file Catalog |

### Documenti Word per Mac (.mcw)

| Scheda | Descrizione |
|---|---|
| **Word - MCW Hidden Text** | Estrae il testo nascosto post-ETX dai file `.mcw` con decodifica custom Mac Roman |
| **Word - Confronto Stesure** | Confronta la prima stesura (decodifica HEX) con la versione finale (via LibreOffice); evidenzia le differenze riga per riga e genera diff HTML |
| **Split Word Segments** | Divide un file binario grezzo in segmenti Word separati dai marker `0xFE37` / `0xFE34` |

### Strumenti

| Scheda | Descrizione |
|---|---|
| **UTILS - Hex → ASCII Decoder** | Decodifica manuale di stringhe esadecimali con mappa custom Mac Roman/Word |

---

## Requisiti

### Python

Versione minima: **Python 3.10**

Installa le dipendenze con:

```bash
pip install -r requirements.txt
```

Le dipendenze di terze parti sono `ttkthemes`, `pandas` e `matplotlib`.

> **Nota per Linux:** `tkinter` non è incluso nella stdlib di default su alcune distribuzioni.
> Installalo con:
> ```bash
> sudo apt install python3-tk   # Debian/Ubuntu
> sudo dnf install python3-tkinter  # Fedora
> ```

### LibreOffice

La funzione **Word - Confronto Stesure** richiede LibreOffice installato sul sistema.

| Sistema | Download |
|---|---|
| Windows | [libreoffice.org](https://www.libreoffice.org/download/download/) |
| macOS | [libreoffice.org](https://www.libreoffice.org/download/download/) |
| Linux | `sudo apt install libreoffice` |

Su Windows, `soffice.exe` deve trovarsi in `C:\Program Files\LibreOffice\program\` oppure essere disponibile nel `PATH` di sistema.

---

## Installazione e avvio

```bash
git clone https://github.com/mariangiglio/eFFeQuadro.git
cd eFFeQuadro
pip install -r requirements.txt
python main.py
```

---

## Struttura del progetto

```
eFFeQuadro/
├── main.py          # Entry point — avvia la GUI
├── gui.py           # Interfaccia grafica (tkinter + ttkthemes)
├── core.py          # Funzioni di parsing e analisi (HFS, MCW, MDB…)
├── hexmap.py        # Mappa esadecimale custom Mac Roman + funzione di decodifica
├── i18n.py          # Testi dell'interfaccia in italiano e inglese
├── logo.ico         # Icona applicazione (opzionale)
├── requirements.txt
├── CITATION.cff     # Metadati per la citazione
├── .gitignore
├── LICENSE
├── README.md        # Documentazione in inglese
└── README.it.md     # Documentazione in italiano
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
- LibreOffice — conversione e lettura file `.mcw`

---

## Lingua

La lingua dell'interfaccia si può cambiare in qualsiasi momento dal menu **🌐 Lingua / Language**. Il cambio ricarica l'interfaccia, quindi gli eventuali risultati aperti vengono chiusi.

Al primo avvio il programma usa la lingua del sistema (italiano se il sistema è in italiano, altrimenti inglese). La scelta viene salvata in un piccolo file di impostazioni nella cartella home dell'utente (`.effequadro.json`).

---

## Temi grafici

L'interfaccia supporta più temi visivi selezionabili dal menu **🎨 Temi**:
`aquativo`, `adapta`, `black`, `blue`, `breeze`, `clearlooks`, `itft1`, `kroc`, `plastik`, `radiance`, `xpnative`.

---

## Come citare

Se usi eFFeQuadro nella tua ricerca, ti chiedo di citarlo. I metadati per la citazione sono nel file [CITATION.cff](CITATION.cff); il pulsante **"Cite this repository"** di GitHub (colonna destra) li restituisce in formato APA e BibTeX.

> Giglio, M. (2026). *eFFeQuadro — Forensic Toolkit* (Versione 1.0.0) [Software]. Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX

---

## Autore

**Mariangela Giglio**
Alma Mater Studiorum — Università di Bologna
GitHub: [github.com/mariangiglio](https://github.com/mariangiglio)

---

## Licenza

Distribuito con licenza **MIT** — vedi il file [LICENSE](LICENSE).

Il software è libero da usare, modificare e ridistribuire, anche a fini commerciali,
a condizione di mantenere la nota di copyright. È fornito "così com'è", senza garanzie.
