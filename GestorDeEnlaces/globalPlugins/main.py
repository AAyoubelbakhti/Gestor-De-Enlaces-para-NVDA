import globalVars
import os
import globalPluginHandler
from scriptHandler import script
import wx
import webbrowser
import json

class LinkManager(wx.Dialog):
    def __init__(self, parent, title):
        super(LinkManager, self).__init__(parent, title=title, size=(500, 400))
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.vbox)

        self.linkList = wx.ListCtrl(self.panel, style=wx.LC_REPORT)
        self.linkList.InsertColumn(0, 'Titulo', width=400)
        self.links = {}
        self.loadLinks()
        self.vbox.Add(self.linkList, proportion=1, flag=wx.EXPAND)

        self.addLinkPanel = wx.Panel(self.panel)
        addLinkBox = wx.BoxSizer(wx.HORIZONTAL)

        lblTitle = wx.StaticText(self.addLinkPanel, label="Título:")
        self.txtTitle = wx.TextCtrl(self.addLinkPanel)
        lblUrl = wx.StaticText(self.addLinkPanel, label="URL:")
        self.txtUrl = wx.TextCtrl(self.addLinkPanel)
        self.addBtn = wx.Button(self.addLinkPanel, label='Guardar')
        self.addBtn.Bind(wx.EVT_BUTTON, self.onAddOrEditLink)

        addLinkBox.Add(lblTitle, flag=wx.RIGHT, border=5)
        addLinkBox.Add(self.txtTitle, proportion=1, flag=wx.EXPAND | wx.RIGHT, border=5)
        addLinkBox.Add(lblUrl, flag=wx.RIGHT, border=5)
        addLinkBox.Add(self.txtUrl, proportion=1, flag=wx.EXPAND | wx.RIGHT, border=5)
        addLinkBox.Add(self.addBtn)
        self.addLinkPanel.SetSizer(addLinkBox)
        self.addLinkPanel.Hide()

        self.vbox.Add(self.addLinkPanel, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=10)

        self.linkList.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.openLink)
        self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)

        self.editingIndex = None 

        self.Centre()
        self.Show()

    def getJsonPath(self):
        return os.path.join(globalVars.appArgs.configPath, "links.json")

    def loadLinks(self):
        self.linkList.DeleteAllItems()
        self.links.clear()
        path = self.getJsonPath()
        try:
            with open(path, 'r') as file:
                self.links = json.load(file)
                for title, url in self.links.items():
                    self.linkList.InsertItem(self.linkList.GetItemCount(), title)
        except FileNotFoundError:
            print(f"Archivo no encontrado: {path}. Se creará uno nuevo al añadir un enlace.")
            self.saveLinks()
        except json.JSONDecodeError:
            print("Error al decodificar JSON. Verifique el contenido del archivo.")
            self.saveLinks()

    def saveLinks(self):
        with open(self.getJsonPath(), 'w') as file:
            json.dump(self.links, file)

    def onAddOrEditLink(self, event):
        title = self.txtTitle.GetValue()
        url = self.txtUrl.GetValue()
        if self.editingIndex is None:
            if title and url and title not in self.links:
                self.links[title] = url
                self.saveLinks()
                wx.MessageBox('Enlace añadido', 'Info', wx.OK | wx.ICON_INFORMATION)
                self.loadLinks()
            elif title in self.links:
                wx.MessageBox('Un enlace con este título ya existe', 'Error', wx.OK | wx.ICON_ERROR)
        else:
            existing_title = self.linkList.GetItemText(self.editingIndex)
            if title and url:
                if title != existing_title and title in self.links:
                    wx.MessageBox('Un enlace con este título ya existe', 'Error', wx.OK | wx.ICON_ERROR)
                else:
                    del self.links[existing_title]
                    self.links[title] = url
                    self.saveLinks()
                    wx.MessageBox('Enlace actualizado', 'Info', wx.OK | wx.ICON_INFORMATION)
            self.editingIndex = None
            self.addLinkPanel.Hide()
            self.panel.Layout()

    def deleteLink(self):
        index = self.linkList.GetFirstSelected()
        if index != -1:
            title = self.linkList.GetItemText(index)
            if title in self.links:
                del self.links[title]
                self.saveLinks()
                wx.MessageBox('Enlace borrado', 'Info', wx.OK | wx.ICON_INFORMATION)

    def openLink(self, event):
        title = self.linkList.GetItemText(event.GetIndex())
        url = self.links.get(title)
        if url:
            webbrowser.open(url)

    def onKeyPress(self, event):
        keycode = event.GetKeyCode()
        if event.ControlDown() and keycode == ord('A'):
            self.toggleAddLinkPanel()
        elif event.ControlDown() and keycode == ord('E'):
            self.editLink()
        elif event.ControlDown() and keycode == ord('B'):
            self.deleteLink()
        event.Skip()

    def toggleAddLinkPanel(self):
        if self.addLinkPanel.IsShown():
            self.addLinkPanel.Hide()
        else:
            self.addLinkPanel.Show()
            self.txtTitle.SetFocus()
        self.panel.Layout()

    def editLink(self):
        index = self.linkList.GetFirstSelected()
        if index != -1:
            title = self.linkList.GetItemText(index)
            url = self.links.get(title)
            self.txtTitle.SetValue(title)
            self.txtUrl.SetValue(url)
            self.editingIndex = index
            if not self.addLinkPanel.IsShown():
                self.addLinkPanel.Show()
                self.panel.Layout()
            self.txtTitle.SetFocus()

def start_link_manager():
    frame = LinkManager(None,'Gestor de Enlaces')

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    @script(description='Abre la ventana del gestor de enlaces', gesture='kb:NVDA+alt+k', category='Gestor De Enlaces')
    def script_open_file(self, gesture):
        wx.CallAfter(start_link_manager)
