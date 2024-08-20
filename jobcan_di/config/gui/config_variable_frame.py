"""
A frame for variable of configuration.

Classes
-------
- `ConfigVariableFrame` : A frame for variable of configuration
"""
from typing import Union

import customtkinter as ctk

from config_editor import ConfigVariable, RangeType, check_range
from ._base import JP_FONT_NAME, ValidationType, count_text_width



class ConfigVariableFrame(ctk.CTkFrame):
    """
    A frame for variable of configuration.
    """
    def __init__(self, master, variable:ConfigVariable, name:str,
                 title_font=Union[tuple, ctk.CTkFont, None],
                 text_font=Union[tuple, ctk.CTkFont, None],
                 **kwargs):
        """Create ConfigVariableFrame instance

        Args
        ----
        master : tk.Widget
            Parent widget
        variable : ConfigVariable
            ConfigVariable instance
        font : Union[tuple, ctk.CTkFont, None]
            Font for the title"""
        super().__init__(master, **kwargs)
        self.name = name
        self.variable = variable
        self.title_font = title_font
        self.text_font = text_font
        self.jp_text_font = ctk.CTkFont(family=JP_FONT_NAME, size=self.text_font.cget("size"),
                                        weight=self.text_font.cget("weight"))
        self.calculated_description_height:int = 0

        self._create_widgets()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        # Create label
        self.label = ctk.CTkLabel(self, text=self.name,
                                 font=self.title_font, fg_color="transparent",
                                 anchor="w")
        self.label.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=10)

        # Add description
        text = "\n\n".join(self.variable.description)
        self.description = ctk.CTkTextbox(self, font=self.jp_text_font,
                                          border_width=0, activate_scrollbars=False,
                                          fg_color="transparent", bg_color="transparent")
        self.description.insert(ctk.END, text)
        fh = self.text_font.cget("size")
        r_wid = self.description.winfo_reqwidth()
        n_lines = (sum([max(1, round(fh/2*count_text_width(line)/r_wid))
                        for line in self.variable.description])
                   + (len(self.variable.description)-1))
        self.calculated_description_height = int(n_lines*fh*1.5)
        self.description.configure(state=ctk.DISABLED, height=self.calculated_description_height)
        self.description.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))

        # Create input widget
        if self.variable.type == bool:
            # Bool type
            self.input_widget = ctk.CTkCheckBox(
                self, font=self.text_font,
                text= "Enabled" if self.variable.value else "Disabled"
            )
            if self.variable.value:
                self.input_widget.select()
            # Set command for checkbox to change text and validate
            change_text = lambda var=self.input_widget: var.configure(text="Enabled" if var.get() else "Disabled")
            self.input_widget.configure(command=lambda: (change_text, self._selection_changed()))
        elif self.variable.range_type == RangeType.SET:
            # Set type
            options = self.variable.range
            self.input_widget = ctk.CTkOptionMenu(self, values=options,
                                                 font=self.text_font,
                                                 height=int(self.text_font.cget("size")*2),
                                                 command= (lambda e: self._selection_changed()))
            self.input_widget.set(self.variable.value)
            # Set command for option menu to validate
        else:
            # Other types
            self.input_widget = ctk.CTkEntry(self, font=self.text_font,
                                             validatecommand=(self._validate_entry),
                                             validate="focusout",
                                             placeholder_text=str(self.variable.default))
            self.input_widget.insert(0, str(self.variable.value))
            self.input_widget.focus()
            # Bind enter key to validate entry (focus out)
            self.input_widget.bind("<Return>", lambda e: self.focus())

        self.validate_label = ctk.CTkLabel(self, width=75, font=self.text_font)
        self._update_validation(ValidationType.SAVED)
        self.validate_label.grid(row=2, column=0, sticky="w", padx=(20,0), pady=10)
        if (self.variable.type in [int, float]) and (self.variable.range_type != RangeType.SET):
            # Broader entry widget (for int and float types; to show longer error messages)
            #   e.g. "INVALID TYPE", "OUT OF RANGE"
            self.validate_label.configure(width=120)
            self.input_widget.grid(row=2, column=1, padx=20, pady=10, sticky="ew")
            self._add_type_suggestion()
        else:
            self.input_widget.grid(row=2, column=1, columnspan=2, sticky="ew", padx=20, pady=10)

    def _add_type_suggestion(self):
        """Add type suggestion to the input widget for integer and decimal types"""
        _type = "integer" if self.variable.type == int else "decimal"
        if self.variable.range_type == RangeType.LIST_E_E:
            range_str = f"range: {self.variable.range[0]} ≦ value ≦ {self.variable.range[1]}"
        elif self.variable.range_type == RangeType.LIST_E_NE:
            range_str = f"range: {self.variable.range[0]} ≦ value < {self.variable.range[1]}"
        elif self.variable.range_type == RangeType.LIST_NE_E:
            range_str = f"range: {self.variable.range[0]} < value ≦ {self.variable.range[1]}"
        elif self.variable.range_type == RangeType.LIST_NE_NE:
            range_str = f"range: {self.variable.range[0]} < value < {self.variable.range[1]}"
        else:
            range_str = ""

        suggestion = ctk.CTkLabel(self, text=f"Enter {_type} value. ({range_str})",
                                  font=self.text_font, text_color=["gray54", "gray54"],
                                  fg_color="transparent", anchor="e")
        suggestion.grid(row=3, column=0, columnspan=2, sticky="e", padx=(0,20), pady=(0,10))

    def _update_validation(self, validation_type:ValidationType):
        """Update validation label"""
        if validation_type == ValidationType.SAVED:
            self.validate_label.configure(text="SAVED", text_color=["gray54", "gray54"])
        elif validation_type == ValidationType.OK:
            self.validate_label.configure(text="OK", text_color="green")
        elif validation_type == ValidationType.INVALID_TYPE:
            self.validate_label.configure(text="INVALID TYPE", text_color="red")
        elif validation_type == ValidationType.OUT_OF_RANGE:
            self.validate_label.configure(text="OUT OF RANGE", text_color="red")

    def _validate_entry(self):
        """Validate entry widget"""
        try:
            new_value = self.variable.type(self.input_widget.get())
        except ValueError:
            self._update_validation(ValidationType.INVALID_TYPE)
            return False

        if new_value == self.variable.value:
            # Do nothing if the value is not changed
            self._update_validation(ValidationType.SAVED)
            return True

        if not check_range(new_value, self.variable.range_type, self.variable.range):
            self._update_validation(ValidationType.OUT_OF_RANGE)
            return False

        # Validated
        self._update_validation(ValidationType.OK)
        return True

    def _selection_changed(self):
        """Selection changed event for OptionMenu and CheckBox widgets"""
        if isinstance(self.input_widget, ctk.CTkOptionMenu):
            if self.variable.value != self.input_widget.get():
                self._update_validation(ValidationType.OK)
            else:
                self._update_validation(ValidationType.SAVED)
        elif isinstance(self.input_widget, ctk.CTkCheckBox):
            if self.variable.value != self.input_widget.get():
                self._update_validation(ValidationType.OK)
            else:
                self._update_validation(ValidationType.SAVED)

    def mark_as_saved(self):
        """Mark the variable as saved"""
        if self.validate_label.cget("text") != "OK":
            # Do nothing if the value is not validated
            return

        # Update variable value (if not changed)
        if (new_value:=self.variable.type(self.input_widget.get())) != self.variable.value:
            self.variable.value = new_value

        self._update_validation(ValidationType.SAVED)

    def restore(self):
        """Restore the variable value"""
        if self.validate_label.cget("text") == "SAVED":
            # Do nothing if the value is not changed
            return

        if isinstance(self.input_widget, ctk.CTkEntry):
            self.input_widget.delete(0, ctk.END)
            self.input_widget.insert(0, str(self.variable.value))
        elif isinstance(self.input_widget, ctk.CTkOptionMenu):
            self.input_widget.set(self.variable.value)
        elif isinstance(self.input_widget, ctk.CTkCheckBox):
            if self.variable.value:
                self.input_widget.select()
            else:
                self.input_widget.deselect()

        self._update_validation(ValidationType.SAVED)

    def is_saved(self):
        """Check if the variable is saved"""
        return self.validate_label.cget("text") == "SAVED"
