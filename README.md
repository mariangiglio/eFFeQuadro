# eFFeQuadro — Forensic Toolkit

**English** · [Italiano](README.it.md)

A forensic analysis tool for HFS volumes and Microsoft Word for Macintosh documents from the classic Mac era (1980s–1990s).

It was developed to support research and documentary analysis on historical storage media (floppy disks, HFS disk images), in the context of forensic philology applied to born-digital literary archives.

The interface is available in **English and Italian**: switch language from the **🌐 Lingua / Language** menu. The choice is remembered for the next session.

---

## Features

### HFS file system

| Tab | Description |
|---|---|
| **File Info** | Identifies file types by magic bytes and file name (Word, MDB, Catalog, etc.) |
| **HFS - Allocation & Extents** | Analyses the allocation bitmap and the Extents Overflow file (HFS and HFS+); shows free/used blocks and the extents of fragmented files |
| **HFS - Catalog** | Reads the HFS Catalog B-tree; filters by name, type, year and date field; exports to text |
| **HFS - MDB Header** | Extracts Master Directory Block metadata (signature, dates, volume label, blocks) |
| **HFS - Delete-Log** | Scans unallocated space for deleted Word fragments |
| **HFS - Catalog Date Analysis** | Extracts and plots dates (creation, modification, backup) from one or more Catalog files |

### Word for Macintosh documents (.mcw)

| Tab | Description |
|---|---|
| **Word - MCW Hidden Text** | Extracts hidden post-ETX text from `.mcw` files using a custom Mac Roman decoding |
| **Word - Draft Comparison** | Compares the first draft (HEX decoding) with the final version (via LibreOffice); highlights line-by-line differences and generates an HTML diff |
| **Split Word Segments** | Splits a raw binary file into separate Word segments at the `0xFE37` / `0xFE34` markers |

### Tools

| Tab | Description |
|---|---|
| **UTILS - Hex → ASCII Decoder** | Manual decoding of hexadecimal strings with a custom Mac Roman/Word map |

---

## Requirements

### Python

Minimum version: **Python 3.10**

Install the dependencies with:

```bash
pip install -r requirements.txt
```

The third-party dependencies are `ttkthemes`, `pandas` and `matplotlib`.

> **Linux note:** on some distributions `tkinter` is not installed with Python by default.
> Install it with:
> ```bash
> sudo apt install python3-tk        # Debian/Ubuntu
> sudo dnf install python3-tkinter   # Fedora
> ```

### LibreOffice

The **Word - Draft Comparison** feature requires LibreOffice.

| System | Download |
|---|---|
| Windows | [libreoffice.org](https://www.libreoffice.org/download/download/) |
| macOS | [libreoffice.org](https://www.libreoffice.org/download/download/) |
| Linux | `sudo apt install libreoffice` |

On Windows, `soffice.exe` must be located in `C:\Program Files\LibreOffice\program\` or be available on the system `PATH`.

---

## Installation and launch

```bash
git clone https://github.com/mariangiglio/eFFeQuadro.git
cd eFFeQuadro
pip install -r requirements.txt
python main.py
```

---

## Project structure

```
eFFeQuadro/
├── main.py          # Entry point — launches the GUI
├── gui.py           # Graphical interface (tkinter + ttkthemes)
├── core.py          # Parsing and analysis functions (HFS, MCW, MDB…)
├── hexmap.py        # Custom Mac Roman hex map + decoding function
├── i18n.py          # Interface texts in English and Italian
├── logo.ico         # Application icon (optional)
├── requirements.txt
├── CITATION.cff     # Citation metadata
├── .gitignore
├── LICENSE
├── README.md        # English documentation
└── README.it.md     # Italian documentation
```

---

## Supported inputs

Input files are typically extracted from HFS floppy disk images with tools such as [HFSExplorer](https://www.catacombae.org/hfsexplorer/) or FTK Imager.

| File | Location in the HFS volume |
|---|---|
| `catalog` | Volume root |
| `mdb` / `mdb backup` | Volume root |
| `extents` | Volume root |
| `allocation` | Volume root |
| `delete-log` | Second level, not always present |
| `*.mcw` | User folders in the volume |
| Raw binary file (e.g. `1794`) | `[unallocated space]` folder |

---

## Recommended companion tools

- [hexed.it](https://hexed.it) — online hex viewer for preliminary inspection
- LibreOffice — conversion and reading of `.mcw` files

---

## Language

The interface language can be changed at any time from the **🌐 Lingua / Language** menu. Changing language reloads the interface, so any open results are closed.

On first launch the program uses the system language (Italian if the system is set to Italian, English otherwise). The choice is saved in a small settings file in the user's home folder (`.effequadro.json`).

---

## Themes

The interface supports several visual themes, selectable from the **🎨 Themes** menu:
`aquativo`, `adapta`, `black`, `blue`, `breeze`, `clearlooks`, `itft1`, `kroc`, `plastik`, `radiance`, `xpnative`.

---

## How to cite

If you use eFFeQuadro in your research, please cite it. Citation metadata are provided in [CITATION.cff](CITATION.cff); GitHub's **"Cite this repository"** button (right-hand sidebar) generates APA and BibTeX formats.

> Giglio, M. (2026). *eFFeQuadro — Forensic Toolkit* (Version 1.0.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX

---

## Author

**Mariangela Giglio**
Alma Mater Studiorum — Università di Bologna
GitHub: [github.com/mariangiglio](https://github.com/mariangiglio)

---

## License

Released under the **MIT** license — see the [LICENSE](LICENSE) file.

The software is free to use, modify and redistribute, including for commercial purposes,
provided the copyright notice is retained. It is provided "as is", without warranty of any kind.
