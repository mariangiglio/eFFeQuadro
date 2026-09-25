from ttkthemes import ThemedTk
from gui import HFSToolkitGUI

if __name__ == "__main__":
    root = ThemedTk(theme="itft1")
    try:
        root.state("zoomed")          # Windows (e macOS)
    except Exception:
        try:
            root.attributes("-zoomed", True)   # Linux
        except Exception:
            pass                      # finestra alle dimensioni predefinite
    HFSToolkitGUI(root)
    root.mainloop()
