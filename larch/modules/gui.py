#!/usr/bin/env python
#
# gui.py
#
# (c) Copyright 2009 Michael Towers (larch42 at googlemail dot com)
#
# This file is part of the larch project.
#
#    larch is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    larch is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with larch; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#----------------------------------------------------------------------------
# 2010.03.22

from uipi import Uipi
import locale, os
# Try to work around problems when the system encoding is not utf8
encoding = locale.getdefaultlocale()[1]
if encoding == "UTF8":
    encoding = None


class Ui(Uipi):
    def __init__(self, guiexec):
        if guiexec and os.path.isfile(base_dir + "/" + guiexec):
            guiexec = base_dir + "/" + guiexec
        Uipi.__init__(self, backend=guiexec, cwd=base_dir)

    def init(self):
        # Build the main window
        self.widget("Window", ":larch", title="larch", size="700_500",
                icon="images/larchicon.png", closesignal="$$$uiclose$$$")

        # - Header
        self.widget("Label", ":image", image="images/larch80.png")
        self.widget("Label", ":header", html='<h1><span '
                'style="color:#c55500;">%s</span></h1>'
                % _("<em>larch</em> Live Arch Linux Construction Kit"))
        self.widget("Button", "^:showlog", text=_("View Log"),
                tt=_("This button switches to the log viewer"))
        self.widget("Button", "^:docs", text=_("Help"),
                tt=_("This button switches to the documentation viewer"))
        self.widget("Button", ":quit", text=_("Quit"),
                tt=_("Stop the current action and quit the program"))
        self.addsignal(":quit", "clicked", sname="$$$uiquit$$$")

        # - Main widget
        self.widget("Stack", ":tabs", pages=["tab:main",
                "tab:progress", "tab:log", "tab:doc", "tab:edit"])

        self.widget("Notebook", "^:notebook", tabs=[
                (":page_settings", _("Project Settings")),
                (":page_installation", _("Installation")),
                (":page_larchify", _("Larchify")),
                (":page_medium", _("Prepare Medium")),
                (":page_tweaks", _("Installation Tweaks")),
            ])

        self.layout(":larch", ["*VBOX*",
                ["*HBOX*", ":image",
                    ["*VBOX*",
                        ["*HBOX*", ":header", "*SPACE"],
                        ["*HBOX*", ":showlog", ":docs",
                                "*SPACE", ":quit"],]],
                ":tabs"])

        self.layout("tab:main", ["*VBOX*", ":notebook"])

        self.progress = Progress()
        self.logger = Logger()
        self.docviewer = DocViewer()
        self.editor = Editor()

        self.setDisableWidgets(":larch", [":notebook"])
        self.runningtab(0)

        # A list-choice popup widget
        self.listpopup = Popuplist()
        self.popuplist = self.listpopup.popup


    def go(self):
        self.command(":larch.show")


    def unbusy(self, ok=True):
        # 'ok' is only used by the console interface
        Uipi.unbusy(self)


    def runningtab(self, i=-1):
        if i < 0:
            i = self.maintab
        elif i < 2:
            self.maintab = i
        self.command(":tabs.set", i)



#TODO: progress bar?
class Progress:
    def __init__(self):
        self.active = False

        ui.widget("Label", "progress:header",
            html='<h2>%s</h2><p>%s</p>' % (_("Processing ..."),
            _("Here you can follow the detailed, low-level progress"
            " of the commands.")))
        ui.widget("TextEdit", "progress:text", ro=True)
        ui.widget("LineEdit", "progress:progress", ro=True,
                tt=_("An indication of the progress of the current operation, if possible"))
        ui.widget("Button", "progress:cancel", text=_("Cancel"),
                tt=_("Stop the current action"))
        ui.widget("Button", "^progress:done", text=_("Done"))

        ui.layout("tab:progress", ["*VBOX*", "progress:header",
                ["*HBOX*", "progress:text",
                    ["*VBOX*", "progress:cancel",
                            "*SPACE", "progress:done"]],
                "progress:progress"])

        ui.addsignal("progress:cancel", "clicked", sname="$$$cancel$$$")
        ui.addslot("progress:done*clicked", self._done)

    def _done(self):
        ui.runningtab(0)

    def start(self):
        ui.command("progress:text.x__text")
        ui.command("progress:progress.x__text")
        ui.command("progress:done.enable", False)
        ui.command("progress:cancel.enable", True)
        self.active = True
        ui.runningtab(1)

    def end(self):
        ui.command("progress:cancel.enable", False)
        ui.command("progress:done.enable", True)
        self.active = False

    def addLine(self, line):
        # Try to work around problems when the system encoding is not utf8
        if encoding:
            line = line.decode(self.encoding, "replace").encode("UTF8")
        ui.command("progress:text.append_and_scroll", line)

    def set(self, text=""):
        ui.command("progress:progress.x__text", text)


class Logger:
    def __init__(self):
        ui.widget("Label", "log:header",
            html='<h2>%s</h2><p>%s</p>' % (_("Low-level Command Logging"),
            _("Here you can follow the detailed, low-level progress"
            " of the commands.")))
        ui.widget("TextEdit", "log:text", ro=True)
        ui.widget("Button", "^log:clear", text=_("Clear"))
        ui.widget("Button", "^log:hide", text=_("Hide"),
                tt=_("Go back to the larch controls"))

        ui.layout("tab:log", ["*VBOX*", "log:header",
                ["*HBOX*", "log:text",
                    ["*VBOX*", "log:clear", "*SPACE", "log:hide"]]])

        ui.addslot("log:clear*clicked", self.clear)
        ui.addslot("log:hide*clicked", self._hide)

    def clear(self):
        ui.command("log:text.x__text")

    def addLine(self, line):
        # Try to work around problems when the system encoding is not utf8
        if encoding:
            line = line.decode(self.encoding, "replace").encode("UTF8")
        ui.command("log:text.append_and_scroll", line)

    def _hide(self):
        ui.runningtab()


class DocViewer:
    def __init__(self):
        self.index = self._getPage("index.html")
        self.home = None
        ui.widget("Label", "doc:header",
            html='<h2>%s</h2>' % _("Documentation"))
        ui.widget("HtmlView", "doc:content")
        ui.widget("Button", "^doc:hide", text=_("Hide"),
                tt=_("Go back to the larch controls"))
        ui.widget("Button", "^doc:back", icon="left",
                tt=_("Go back in the viewing history"))
        ui.widget("Button", "^doc:forward", icon="right",
                tt=_("Go forward in the viewing history"))
        ui.widget("Button", "^doc:home", icon="reload",
                tt=_("Reload the documentation for the current larch tab"))
        ui.widget("Button", "^doc:parent", icon="up",
                tt=_("Go to the general larch documentation index"))

        ui.layout("tab:doc", ["*VBOX*", "*HLINE",
                ["*HBOX*", "doc:header", "*SPACE", "doc:back", "doc:forward",
                        "doc:home", "doc:parent", "doc:hide"],
                "doc:content"])

        command.addconnections([
                ("doc:hide*clicked", self._hide),
                ("doc:back*clicked", self._back),
                ("doc:forward*clicked", self._forward),
                ("doc:home*clicked", self.gohome),
                ("doc:parent*clicked", self.goto),
            ])

    def _hide(self):
        ui.runningtab()

    def _back(self):
        ui.command("doc:content.prev")

    def _forward(self):
        ui.command("doc:content.next")

    def _getPage(self, page):
        if lang and (len(lang) > 1):
            p = base_dir + ("/docs/%s/html/" % lang[0:2]) + page
            if os.path.isfile(p):
                return p
        return base_dir + "/docs/html/" + page

    def gohome(self, home=None):
        if home:
            self.home = self._getPage(home)
        self.goto(self.home)

    def goto(self, path=None):
        if not path:
            path = self.index
        ui.command("doc:content.setUrl", path)


class Editor:
    def __init__(self):
        ui.widget("Label", "edit:header",
            html='<h2>%s</h2>' % _("Editor"))
        ui.widget("Label", "edit:title")
        ui.widget("TextEdit", "edit:content")
        ui.widget("Button", "^edit:ok", text=_("OK"))
        ui.widget("Button", "^edit:cancel", text=_("Cancel"))
        ui.widget("Button", "^edit:revert", text=_("Revert"),
                tt=_("Restore the text to its initial state"))
        ui.widget("Button", "^edit:copy", text=_("Copy"))
        ui.widget("Button", "^edit:cut", text=_("Cut"))
        ui.widget("Button", "^edit:paste", text=_("Paste"))
        ui.widget("Button", "^edit:undo", text=_("Undo"))
        ui.widget("Button", "^edit:redo", text=_("Redo"))

        ui.layout("tab:edit", ["*VBOX*",
                ["*HBOX*", "edit:header", "*SPACE", "edit:title"],
                ["*HBOX*", "edit:content",
                    ["*VBOX*", "edit:copy", "edit:cut", "edit:paste",
                        "edit:undo", "edit:redo", "edit:revert",
                        "*SPACE", "edit:cancel", "edit:ok"]]])

    def start(self, title, endcall, text="", revert=None):
        ui.command("edit:title.x__text", title)
        self.endcall = endcall
        self.revert = revert
        try:
            self.text0 = revert() if text == None else text
        except:
            run_error("BUG: Editor - no revert function?")
        ui.command("edit:content.x__text", self.text0)
        command.addconnections([
                ("edit:ok*clicked", self.ok),
                ("edit:cancel*clicked", self.cancel),
                ("edit:revert*clicked", self.dorevert),
                ("edit:copy*clicked", self.copy),
                ("edit:cut*clicked", self.cut),
                ("edit:paste*clicked", self.paste),
                ("edit:undo*clicked", self.undo),
                ("edit:redo*clicked", self.redo),
                ("$edit-done$", self.sendtext),
            ])
        ui.runningtab(4)

    def ok(self):
        ui.asknowait("edit:content.get", "$edit-done$")

    def sendtext(self, text):
        self.endcall(text)
        ui.runningtab()

    def cancel(self):
        ui.runningtab()

    def dorevert(self):
        if self.revert:
            self.text0 = self.revert()
        ui.command("edit:content.x__text", self.text0)

    def copy(self):
        ui.command("edit:content.copy")

    def cut(self):
        ui.command("edit:content.cut")

    def paste(self):
        ui.command("edit:content.paste")

    def undo(self):
        ui.command("edit:content.undo")

    def redo(self):
        ui.command("edit:content.redo")


class Popuplist:
    def __init__(self):
        ui.widget("Dialog",  "popuplist", icon="images/larchicon.png")
        ui.widget("Label", "popuplist:label")
        ui.widget("ListChoice", "^popuplist:list")
        ui.widget("DialogButtons", "popuplist:buttons",
                buttons=("Save", "Discard"), dialog="popuplist")
        ui.layout("popuplist", ["*VBOX*", "popuplist:label", "popuplist:list",
                "popuplist:buttons"])
        ui.addslot("popuplist:list*changed", self.callback)

    def popup(self, items, index=0, title=_("Choose an item"),
            text=_("Select one of the following items:")):
        ui.command("popuplist.x__title", title)
        ui.command("popuplist:label.x__text", text)
        ui.command("popuplist:list.set", items, index)
        self.choice = index
        return (self.choice if ui.ask("popuplist.showmodal") else None)

    def callback(self, i):
        self.choice = i
