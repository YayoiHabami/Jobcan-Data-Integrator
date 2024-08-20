"""
ConfigEditorGui class

Classes
-------
- `ConfigEditorGui` : GUI for editing config file
"""
import os
from os import path
import tkinter as tk
from tkinter import filedialog
from typing import Optional, Tuple, Dict

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from PIL import Image
from PIL.ImageFile import ImageFile

from config_editor import ConfigEditor
from ._base import EN_FONT_NAME, JP_FONT_NAME, TextType, is_ascii_only
from .collapsible_frame import CollapsibleFrame
from .config_variable_frame import ConfigVariableFrame
from .gui_status import ConfigEditorGuiStatus


class ConfigEditorGui(ctk.CTk):
    """GUI for editing config file
    """
    def __init__(self,
                 title:str="Config Editor",
                 config_path:Optional[str]=None,
                 icon:Optional[str]=None,):
        """Create ConfigEditorGui instance

        Args
        ----
        title : str
            Title of the window
        config_path : str
            Path to config file
        icon : Optional[str]
            Path to icon file (.ico file).
            If not provided, default icon will be used.
        """
        super().__init__()

        # Load status
        self.status = ConfigEditorGuiStatus(path.join(os.getcwd(),
                                                      "editor-status"))
        ctk.set_appearance_mode(self.status.appearance_mode)
        ctk.set_widget_scaling(int(self.status.scaling.replace("%", "")) / 100)
        ctk.set_window_scaling(int(self.status.scaling.replace("%", "")) / 100)
        self.geometry(self.status.geometry)

        self.selected_section: Optional[str] = None
        """Selected section name"""
        self.msg = None
        """Message box for confirmation dialog"""
        self.normal_geometry = []
        """Normal size and position of the window (Geometry before maximized)"""
        self.icons: Dict[str, Tuple[ImageFile]] = {}
        """Icons for the app"""

        self.variable_widget_padding = 10
        """Padding for variable widgets"""

        self.config = ConfigEditor()

        self.title(title)
        # set icon if provided
        if isinstance(icon, str) and path.exists(icon) and icon.endswith(".ico"):
            # set icon if path exists
            self.iconbitmap(icon)

        # fonts
        self.basic_font_size = 14
        self.title_font_size = 20
        self.basic_font = ctk.CTkFont(family=EN_FONT_NAME,
                                      size=self.basic_font_size, weight='normal')
        self.subtitle_font = ctk.CTkFont(family=EN_FONT_NAME,
                                         size=self.basic_font_size, weight='bold')
        self.title_font = ctk.CTkFont(family=EN_FONT_NAME,
                                      size=self.title_font_size, weight='bold')
        self.basic_font_jp = ctk.CTkFont(family=JP_FONT_NAME,
                                         size=self.basic_font_size, weight='normal')
        self.subtitle_font_jp = ctk.CTkFont(family=JP_FONT_NAME,
                                            size=self.basic_font_size, weight='bold')
        self.title_font_jp = ctk.CTkFont(family=JP_FONT_NAME,
                                         size=self.title_font_size, weight='bold')

        # directories)
        self.resource_dir = path.join(os.getcwd(), "resources")
        if path.exists(path.dirname(icon)):
            self.resource_dir = path.dirname(path.dirname(icon))
        elif not path.exists(self.resource_dir):
            self.resource_dir = path.join(os.getcwd(), "jobcan_di/config/resources")

        # Bind events
        self.bind_events()

        # setup gui
        self._setup()
        # if config path is provided, load it
        self.load_config(config_path if config_path else self.status.config_path)

    def bind_events(self):
        """Bind events"""
        # Bind window resize event
        self.bind("<Configure>", self.on_resize)
        self.resize_id = None

        # Bind window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Bind click event
        self.bind("<Button-1>", self.on_click)

        # Bind focus out event
        self.bind("<FocusOut>", self.on_focus_out)

    def load_config(self, config_path:str):
        """Load config file.
        If config_path is not correct or not exists, file dialog will be shown.
        Also, if loading config file fails, error message will be shown,
        and no widgets will be created.

        Args
        ----
        config_path : str
            Path to config file
        """
        # Check if config path is provided and exists
        if not config_path or not path.exists(config_path):
            config_path = filedialog.askopenfilename(parent=self,
                                                     title="Select config file",
                                                     filetypes=[("INI files", "*.ini")],
                                                     initialdir=os.getcwd())
        try:
            config = ConfigEditor(config_path)
        except Exception as e:
            return self._show_error_message("Error", f"Failed to load config file.\n{str(e)}")
        if not config.is_loaded():
            return self._show_error_message("Error", "Failed to load config file.")

        # clear widgets
        self.clear()

        # save config path
        self.status.config_path = config_path
        self.status.save()

        # load config and create widgets
        self.config = config
        self._create_sidebar_widgets()

    def clear(self):
        """Clear all widgets related to config data"""
        # Clear section buttons
        for child in self.section_frame.winfo_children():
            child.destroy()
        # Clear variable widgets
        for column in self.variable_columns:
            for child in column.winfo_children():
                child.destroy()

    def _setup(self):
        """Setup GUI layout"""
        ctk.set_default_color_theme('blue')

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # create left frame (for section buttons and options)
        self.sidebar_frame = ctk.CTkFrame(self, fg_color=("#fcfcfc", "#303030"),
                                          corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="ns")
        # create section frame
        self.section_frame = ctk.CTkScrollableFrame(self.sidebar_frame,
                                                    fg_color="transparent",
                                                    corner_radius=0)
        self.section_frame._scrollbar.configure(width=0)
        self.section_frame.pack(side = ctk.TOP, fill=ctk.BOTH, anchor="n", expand=True)
        # create option frame
        self.option_frame = CollapsibleFrame(self.sidebar_frame,
                                             title="Options", font=self.title_font,
                                             fg_color="transparent")
        self.option_frame.pack(side = ctk.BOTTOM, anchor="s")

        # create right frame (for section widgets)
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color=("#f0f0f0", "#242424"),
                                                 corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        # create configure frame
        self.configure_frame = ctk.CTkFrame(self, fg_color=("#f0f0f0", "#242424"),
                                            corner_radius=0)
        self.configure_frame.grid(row=1, column=1, sticky="sew")
        self._create_configure_widgets()

        # create variable columns
        self.variable_columns: list = []
        self.variable_column_heights: list[int] = []
        self.change_num_columns_event(self.status.num_columns)

    def _get_text_font(self, text_type:TextType, text:str) -> ctk.CTkFont:
        """Get font for text

        Args
        ----
        text_type : TextType
            Text type
        text : str
            Text"""
        if is_ascii_only(text):
            if text_type == TextType.TITLE:
                return self.title_font
            elif text_type == TextType.SUBTITLE:
                return self.subtitle_font
            else:
                return self.basic_font
        else:
            if text_type == TextType.TITLE:
                return self.title_font_jp
            elif text_type == TextType.SUBTITLE:
                return self.subtitle_font_jp
            else:
                return self.basic_font_jp

    def _get_icon(self, icon_name:str, size:tuple[int, int]) -> ctk.CTkImage:
        """Get icon image

        Args
        ----
        icon_name : str
            Icon base name.
            e.g. "default" for "default.png", or "default_light.png" and "default_dark.png"
        size : tuple[int, int]
            Icon size"""
        if icon_name in self.icons:
            # return icon if already loaded
            if len(self.icons[icon_name]) == 2:
                return ctk.CTkImage(light_image=self.icons[icon_name][0],
                                    dark_image=self.icons[icon_name][1],
                                    size=size)
            else:
                return ctk.CTkImage(self.icons[icon_name][0], size=size)

        # load icon
        icon_path1 = path.join(self.resource_dir, "icons", f"{icon_name}.png")
        icon_path2a = path.join(self.resource_dir, "icons", f"{icon_name}_light.png")
        icon_path2b = path.join(self.resource_dir, "icons", f"{icon_name}_dark.png")
        if path.exists(icon_path2a) and path.exists(icon_path2b):
            # load light and dark icons
            self.icons[icon_name] = (Image.open(icon_path2a), Image.open(icon_path2b))
            return ctk.CTkImage(light_image=self.icons[icon_name][0],
                                dark_image=self.icons[icon_name][1],
                                size=size)
        elif path.exists(icon_path1):
            # load icon
            self.icons[icon_name] = (Image.open(icon_path1),)
            return ctk.CTkImage(self.icons[icon_name][0], size=size)
        else:
            # return default icon
            if "default" not in self.icons:
                # load default icon
                self.icons["default"] = (Image.open(path.join(self.resource_dir, "icons", "default_light.png")),
                                         Image.open(path.join(self.resource_dir, "icons", "default_dark.png")))
            return self._get_icon("default", size)

    def _create_sidebar_widgets(self):
        if self.config is None or self.config.is_loaded() == False:
            # config not loaded
            # TODO: show error message
            return

        pad_x = 20
        max_width = self._create_section_buttons()
        max_width = w if (w:=self._create_options(pad_x)) > max_width else max_width

        # configure buttons width
        for child in self.section_frame.winfo_children():
            child.configure(True, width = max_width - 10)

        # change section frame width
        new_width = max_width + 2*pad_x - 10
        self.section_frame.configure(require_redraw=True, width = new_width)
        self.option_frame.configure(require_redraw=True, width = max_width - 10)
        self.sidebar_frame.configure(require_redraw=True, width = new_width)

        # TODO: set minsize

    def _create_section_buttons(self):
        text_color = ("gray10", "gray90")

        self.logo_image = ctk.CTkImage(Image.open(path.join(self.resource_dir, "icons",
                                                            "settings_icon.png")),
                                       size=(64, 64))
        s = ctk.CTkLabel(self.section_frame, text="Menu",
                         text_color=text_color, fg_color="transparent",
                         image = self.logo_image, compound="left",
                         font=self._get_text_font(TextType.TITLE, "Menu"),
                         height=int(self.title_font_size*2.2))
        s.grid(row=0, column=0, padx=10, pady=(10,5), sticky="n")

        # create buttons for each section
        max_width = 0
        for i, section in enumerate(self.config.keys()):
            if self.config[section].tags.get("hidden", 0):
                continue

            icon_name = self.config[section].tags.get("icon", "default")
            display_name = self.config[section].tags.get("display-name", section)

            button = ctk.CTkButton(self.section_frame,
                                   text=display_name,
                                   text_color=text_color,
                                   fg_color="transparent",
                                   hover_color=("#f0f0f0", "#4d4d4d"),
                                   font=self._get_text_font(TextType.SUBTITLE, display_name),
                                   corner_radius=0,
                                   height=int(self.basic_font_size*3),
                                   image = self._get_icon(icon_name, (24, 24)),
                                   border_spacing=15,
                                   command=lambda s=section: self._on_section_click(s),
                                   anchor="w")
            button.grid(row=i+1, column=0, padx=0, pady=0, sticky="ew")
            max_width = s if (s:=button.winfo_reqwidth()) > max_width else max_width

        return max_width

    def _create_options(self, pad_x:int):
        max_width = 0

        # Create appearance mode option
        text = "Appearance Mode:"
        self.appearance_mode_label = ctk.CTkLabel(self.option_frame.content_frame, text=text,
                                                  font=self._get_text_font(TextType.SUBTITLE, text),
                                                  anchor="w")
        self.appearance_mode_label.pack(side=ctk.TOP, fill=ctk.X)
        self.appearance_mode_option_menu = ctk.CTkOptionMenu(self.option_frame.content_frame,
                                                             values=["Light", "Dark", "System"],
                                                             font=self.basic_font,
                                                             height=int(self.basic_font_size*2.2),
                                                             command=self.change_appearance_mode_event)
        self.appearance_mode_option_menu.pack(side=ctk.TOP, fill=ctk.X, pady=(0, pad_x))
        self.appearance_mode_option_menu.set(self.status.appearance_mode)

        # Create scaling option
        text = "UI Scaling:"
        self.scaling_label = ctk.CTkLabel(self.option_frame.content_frame,text=text,
                                          font=self._get_text_font(TextType.SUBTITLE, text),
                                          anchor="w")
        self.scaling_label.pack(side=ctk.TOP, fill=ctk.X)
        self.scaling_option_menu = ctk.CTkOptionMenu(self.option_frame.content_frame,
                                                     values=["80%", "90%", "100%", "110%", "120%"],
                                                     font=self.basic_font,
                                                     height=int(self.basic_font_size*2.2),
                                                     command=self.change_scaling_event)
        self.scaling_option_menu.pack(side=ctk.TOP, fill=ctk.X, pady=(0, pad_x))
        self.scaling_option_menu.set(self.status.scaling)

        # Create number of columns option
        text = "Number of Columns:"
        self.num_columns_label = ctk.CTkLabel(self.option_frame.content_frame, text=text,
                                              font=self._get_text_font(TextType.SUBTITLE, text),
                                              anchor="w")
        self.num_columns_label.pack(side=ctk.TOP, fill=ctk.X)
        self.num_columns_option_menu = ctk.CTkOptionMenu(self.option_frame.content_frame,
                                                         values=["1", "2", "3", "4", "5"],
                                                         font=self.basic_font,
                                                         height=int(self.basic_font_size*2.2),
                                                         command=self.change_num_columns_event)
        self.num_columns_option_menu.pack(side=ctk.TOP, fill=ctk.X, pady=(0, pad_x))
        self.num_columns_option_menu.set(self.status.num_columns)

        max_width = w if (w:=self.appearance_mode_option_menu.winfo_reqwidth()) > max_width else max_width
        max_width = w if (w:=self.scaling_option_menu.winfo_reqwidth()) > max_width else max_width
        max_width = w if (w:=self.num_columns_option_menu.winfo_reqwidth()) > max_width else max_width

        return max_width

    def _create_variable_widgets(self):
        """Create widgets for selected section (based on the number of columns)"""
        if not self.config.is_loaded():
            # config not loaded
            return

        # clear all widgets in each column
        for column in self.variable_columns:
            for child in column.winfo_children():
                # destroy child
                child.destroy()
        self.variable_column_heights = [0] * len(self.variable_columns)

        if self.selected_section is None:
            return

        # create widgets for selected section
        for var in self.config[self.selected_section]:
            if self.config[self.selected_section][var].tags.get("hidden", 0):
                continue
            # select column with minimum height
            min_height = min(self.variable_column_heights)
            column_index = self.variable_column_heights.index(min_height)

            # create widget
            pad_y = (self.variable_widget_padding, self.variable_widget_padding)
            frame = ConfigVariableFrame(self.variable_columns[column_index],
                                        self.config[self.selected_section][var],
                                        name=var,
                                        title_font=self.title_font,
                                        text_font=self.basic_font_jp,
                                        fg_color=["gray100", "gray20"],
                                        corner_radius=10)
            frame.pack(fill=ctk.X, pady=pad_y)

            # update column height
            self.variable_column_heights[column_index] += frame.calculated_description_height

    def _create_configure_widgets(self):
        """Create widgets for configure frame. E.g. save button"""
        # Create discard button
        text_d = "Discard"
        text_s = "Save"
        font = self._get_text_font(TextType.SUBTITLE, text_d + text_s)
        height = int(font.cget("size")*2.5)
        corner_radius = int(height/2.5)
        self.discard_button = ctk.CTkButton(self.configure_frame,
                                           text=text_d,
                                           height=height,
                                           corner_radius=corner_radius,
                                           font=font,
                                           command=self.discard_config_changes)
        self.discard_button.pack(side=ctk.RIGHT, padx=(0,20), pady=10)

        # Create save button
        self.save_button = ctk.CTkButton(self.configure_frame,
                                        text=text_s,
                                        height=height,
                                        corner_radius=corner_radius,
                                        font=font,
                                        command=self.save_config)
        self.save_button.pack(side=ctk.RIGHT, padx=(0, 20), pady=10)

    def _show_error_message(self, title:str, message:str):
        """Show error message"""
        self.msg = CTkMessagebox(master=self, title=title,
                                 message=message, icon="cancel")
        self.msg.get()
        self.msg = None

    def _get_total_scaling_ratio(self):
        """Get total scaling ratio.
        This method returns the total scaling ratio by considering the DPI ratio and the scaling ratio.

        Returns
        -------
        float
            Total scaling ratio"""
        dpi_ratio = self.winfo_fpixels('1i') / 96
        scaling_ratio = int(self.status.scaling.replace("%", "")) / 100
        return dpi_ratio * scaling_ratio

    def _update_min_size(self):
        """Update minimum size of the window. If the current size is smaller than the minimum size, resize the window."""
        # Update minimum size
        # The smaller the scaling ratio, the smaller the minimum size.
        ratio = self._get_total_scaling_ratio() / (int(self.status.scaling.replace("%", "")) / 100)
        min_width = (260 + 500 * int(self.status.num_columns)) / ratio
        min_height = 600 / ratio
        self.minsize(min_width, min_height)

    #
    # Event handlers
    #

    def on_resize(self, event):
        """Event handler for window resize"""
        # Check if the window that triggered the event is the root window
        if event.widget == self:
            # Cancel the previous scheduled event
            if self.resize_id:
                self.after_cancel(self.resize_id)
            # Schedule a new event
            self.resize_id = self.after_idle(self.resize_callback)

    def resize_callback(self):
        """Callback for window resize.
        This method is called after the window is resized and the user has stopped resizing."""
        self.resize_id = None

        # Update latest size (when not maximized)
        if self.state() != "zoomed":
            self.normal_geometry = [self.winfo_width(), self.winfo_height(),
                                    self.winfo_x(), self.winfo_y()]

    def on_closing(self):
        """Event handler for window close"""
        # Check if there are unsaved changes
        if (ij:=self.get_unsaved_config_variable_id()) != []:
            # Show confirmation dialog
            self.msg = CTkMessagebox(master=self, title="Exit?",
                                     message="Do you want to exit without saving changes?",
                                     icon="question",
                                     option_1="Cancel", option_2="No", option_3="Yes")
            # Bind out of focus event
            response = self.msg.get()
            if response != "Yes":
                self.msg = None
                return

        # Save status
        # If the geometry is not initialized, do not save it
        if self.normal_geometry != []:
            # Save the geometry in inches
            # For high DPI displays, the geometry is saved in inches.
            # Also, the scaling ratio is considered.
            ratio = self._get_total_scaling_ratio()
            wxh = f"{int(self.normal_geometry[0] / ratio)}x{int(self.normal_geometry[1] / ratio)}"
            self.status.geometry = f"{wxh}+{self.normal_geometry[2]}+{self.normal_geometry[3]}"
        self.status.save()

        # Close the window
        self.destroy()

    def on_click(self, event):
        """Event handler for click"""
        # Check if the event was triggered by the root window
        if not issubclass(event.widget.__class__, tk.Entry):
            # Clear the focus
            self.focus()

    def on_focus_out(self, event):
        """Event handler for focus out"""
        # Clear the focus
        if self.msg:
            # Focussed on message box
            return
        self.focus()

    def _on_section_click(self, section:str):
        """Create widgets for selected section

        Args
        ----
        section : str
            Section name
        """
        self.select_section(section)

    def select_section(self, section:str):
        """Select section by name

        Args
        ----
        section : str
            Section name
        """
        # Get relation between display name and section name
        display_names = {self.config[s].tags.get("display-name", s): s for s in self.config.keys()}

        # Change button states
        for child in self.section_frame.winfo_children():
            if not isinstance(child, ctk.CTkButton):
                continue

            if self.selected_section and display_names[child.cget("text")] == self.selected_section:
                # Enable previously selected section button
                child.configure(state = ctk.NORMAL)
            if display_names[child.cget("text")] == section:
                # Disable selected section button
                child.configure(state = ctk.DISABLED)

        # Change selected section
        self.selected_section = section
        self._create_variable_widgets()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

        # Update status
        self.status.appearance_mode = new_appearance_mode
        self.status.save()

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)
        ctk.set_window_scaling(new_scaling_float)

        # Update status
        self.status.scaling = new_scaling
        self.status.save()

        # Change minimum size
        self._update_min_size()

    def change_num_columns_event(self, new_num_columns: str):
        # Update status
        self.status.num_columns = new_num_columns
        self.status.save()

        # Change minimum size
        self._update_min_size()

        # Reset column frames
        for child in self.main_frame.winfo_children():
            child.destroy()
        self.variable_columns.clear()
        for i in range(int(new_num_columns)):
            self.variable_columns.append(ctk.CTkFrame(self.main_frame, fg_color="transparent"))
            pad_x = (self.variable_widget_padding, self.variable_widget_padding)
            pad_y = (self.variable_widget_padding, 0)
            self.variable_columns[-1].grid(sticky="nsew", row=0, column=i,
                                           padx=pad_x, pady=pad_y)
            self.main_frame.grid_columnconfigure(i, weight=1)
            self.variable_column_heights.append(0)

        # Recreate widgets
        self._create_variable_widgets()

    def save_config(self):
        """Save config"""
        for column in self.variable_columns:
            for child in column.winfo_children():
                if isinstance(child, ConfigVariableFrame):
                    child.mark_as_saved()
        self.config.save()

    def discard_config_changes(self):
        """Discard config changes"""
        for column in self.variable_columns:
            for child in column.winfo_children():
                if isinstance(child, ConfigVariableFrame):
                    child.restore()

    def get_unsaved_config_variable_id(self):
        """Get ids of unsaved variable widgets

        Returns
        -------
        list[tuple[int, int]]
            List of indices of unsaved variables, e.g. [(i, j), ...]
            Where i is the index of the column and j is the index of the variable
        """
        not_saved = []
        for i, column in enumerate(self.variable_columns):
            for j, child in enumerate(column.winfo_children()):
                if isinstance(child, ConfigVariableFrame) and (not child.is_saved()):
                    not_saved.append((i, j))
        return not_saved