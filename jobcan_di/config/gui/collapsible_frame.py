"""
CollapsibleFrame

A frame that can be collapsed and expanded

Classes
-------
- `CollapsibleFrame` : A frame that can be collapsed and expanded
"""
from typing import Union

import customtkinter as ctk



class CollapsibleFrame(ctk.CTkFrame):
    """
    A frame that can be collapsed and expanded
    """
    def __init__(self, master, title="",
                 font=Union[tuple, ctk.CTkFont, None],
                 first_open=False,
                 **kwargs):
        """Create CollapsibleFrame instance

        Args
        ----
        master : tk.Widget
            Parent widget
        title : str
            Title of the frame
        font : Union[tuple, ctk.CTkFont, None]
            Font for the title
        first_open : bool
            If True, frame will be open by default"""
        super().__init__(master, **kwargs)
        self.title_font = font

        self.title = title
        self.is_collapsed = False
        self.title_frame = None
        self.toggle_button = None
        self.content_frame = None
        self._create_widgets()

        if first_open:
            self.expand()
        else:
            self.collapse()

    def _create_widgets(self):
        self.title_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.title_frame.pack(fill=ctk.X)

        self.toggle_button = ctk.CTkButton(self.title_frame,
                                           height=int(self.title_font.cget("size")*2),
                                           text_color=("black", "white"),
                                           hover_color=("lightgray", "gray20"),
                                           font=self.title_font,
                                           command=self.toggle,
                                           fg_color="transparent")
        self.toggle_button.pack()

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)

    def toggle(self):
        """Toggle collapse/expand state of the frame"""
        if self.is_collapsed:
            self.expand()
        else:
            self.collapse()

    def collapse(self):
        """Collapse the frame"""
        self.content_frame.pack_forget()
        self.is_collapsed = True
        self.toggle_button.configure(text=f"{self.title} ▲")

    def expand(self):
        """Expand the frame"""
        self.content_frame.pack(fill="both", expand=True)
        self.is_collapsed = False
        self.toggle_button.configure(text=f"{self.title} ▼")

    def add(self, widget, **kwargs):
        """Add widget to the content frame

        Args
        ----
        widget : tk.Widget
            Widget to add
        **kwargs
            Keyword arguments to pass to pack() method
        """
        widget.pack(in_=self.content_frame, **kwargs)

    def configure(self, require_redraw:bool=False, **kwargs):
        """Configure the frame

        Args
        ----
        require_redraw : bool
            If True, redraw the frame
        **kwargs
            Keyword arguments to configure the frame
        """
        super().configure(require_redraw=require_redraw, **kwargs)

        if "width" in kwargs:
            self.toggle_button.configure(require_redraw=True, width=kwargs["width"])
            self.content_frame.configure(require_redraw=True, width=kwargs["width"])
        if "height" in kwargs:
            self.toggle_button.configure(require_redraw=True, height=kwargs["height"])
            self.content_frame.configure(require_redraw=True, height=kwargs["height"])
