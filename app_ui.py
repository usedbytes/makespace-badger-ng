#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
from ui import NameBadgeUI, TroveLabelUI, GeneralLabelUI, DatabaseUI, UpdateDelayer
from printer import DisplayPrinter

class BadgerApp(ttk.Frame):
    def __init__(self, master, printer=DisplayPrinter, tagreader=None, db=None, sound=None):
        super().__init__(master)
        self.master = master
        self.pack()

        self.printer = printer
        self.tagreader = tagreader
        self.db = db
        self.sound = sound

        self.nb = ttk.Notebook(self)
        self.nb.pack()

        self.event_add("<<Tag_Present>>", "None")
        self.bind('<<Tag_Present>>', self.handle_tag)

        self.eraser = UpdateDelayer(self, self.clear_screens, update_delay_ms=30000)

        self.event_add("<<Interacted>>", "None")
        self.bind_all('<<Interacted>>', self.handle_interacted)

        self.namebadge_ui = NameBadgeUI(self.nb, self.printer)
        self.trovelabel_ui = TroveLabelUI(self.nb, self.printer)
        self.general_ui = GeneralLabelUI(self.nb, self.printer)
        self.db_ui = DatabaseUI(self.nb, self.db, self.printer)

        self.nb.add(self.namebadge_ui, text="Name Badge")
        self.nb.add(self.trovelabel_ui, text="Storage Label")
        self.nb.add(self.general_ui, text="General Label")
        self.nb.add(self.db_ui, text="Edit Tag")

        if self.tagreader:
            self.wait_for_tag_gone = None
            self.after(100, self.__check_for_tag)

    def __check_for_tag(self):
        tag = self.tagreader.read_tag()
        if tag:
            if tag == self.wait_for_tag_gone:
                self.after(100, self.__check_for_tag)
                return

            self.wait_for_tag_gone = tag
            self.event_generate("<<Tag_Present>>")
        else:
            self.wait_for_tag_gone = None

        self.after(300, self.__check_for_tag)

    def handle_interacted(self, event):
        self.eraser.set_modified()

    def clear_screens(self):
        self.trovelabel_ui.reset()
        self.namebadge_ui.reset()
        self.general_ui.reset()
        self.db_ui.reset()

    def handle_tag(self, event):
        if not self.tagreader:
            return

        self.eraser.set_modified()

        tag = self.tagreader.read_tag()
        if tag and tag == self.wait_for_tag_gone:
            if self.sound:
                self.sound.beep()
            buttons = self.tagreader.read_buttons()
            print(f"tag: {tag.hex()}, buttons: {buttons}")

            # Special case the "General" tag
            if tag.hex() == "4777701c":
                self.nb.select(self.general_ui)
                self.general_ui.reset()
                return

            # All other tags can only be handled if we have a database
            if not self.db:
                return

            # Look up tag details in database
            try:
                name, comment = self.db.lookup(tag)
            except Exception as e:
                print("Tag not in database, enrol it", e)
                self.db_ui.populate(tag, "Your Name", "Your Comment")
                self.nb.select(self.db_ui)
                return

            if buttons == 0: # Print name badge
                self.namebadge_ui.populate(name, comment)
                self.nb.select(self.namebadge_ui)
                self.namebadge_ui.event_generate("<<Print_Label>>")
                self.trovelabel_ui.populate(name, comment)
            elif buttons == 1:
                self.db_ui.populate(tag, name, comment)
                self.nb.select(self.db_ui)
                self.namebadge_ui.populate(name, comment)
            elif buttons == 2: # Show storage tab
                self.trovelabel_ui.populate(name, comment)
                self.nb.select(self.trovelabel_ui)
                self.namebadge_ui.populate(name, comment)
            elif buttons == 3:
                print(f"Erase tag: {tag}")
                try:
                    self.db.delete(tag)
                    self.db_ui.populate(tag, "Your Name", "Your Comment")
                    self.nb.select(self.db_ui)
                except Exception as e:
                    print("Erase failed:", e)
