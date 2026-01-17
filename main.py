from ttkthemes import ThemedTk
from gui import HFSToolkitGUI

if __name__ == "__main__":
    root = ThemedTk(theme="itft1")
    root.state("zoomed")
    HFSToolkitGUI(root)
    root.mainloop()
