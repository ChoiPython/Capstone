import tkinter as tk
from ui import UI

if __name__ == "__main__":
    main_ui = tk.Tk()
    ui = UI(main_ui)
    main_ui.mainloop()