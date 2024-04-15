import globalPluginHandler
from scriptHandler import script
import wx
import webbrowser
import json

class LinkManager(wx.Frame):
    def __init__(self, parent, title):
        super(LinkManager, self).__init__(parent, title=title, size=(500, 400))
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.vbox)

        self.linkList = wx.ListCtrl(self.panel, style=wx.LC_REPORT)
        self.linkList.InsertColumn(0, 'Titulo', width=400)
        self.urlDict = {}
        self.loadLinks()
        self.vbox.Add(self.linkList, proportion=1, flag=wx.EXPAND)

        self.addLinkPanel = wx.Panel(self.panel)
        addLinkBox = wx.BoxSizer(wx.HORIZONTAL)

        lblTitle = wx.StaticText(self.addLinkPanel, label="Título:")
        self.txtTitle = wx.TextCtrl(self.addLinkPanel)
        lblUrl = wx.StaticText(self.addLinkPanel, label="URL:")
        self.txtUrl = wx.TextCtrl(self.addLinkPanel)
        addBtn = wx.Button(self.addLinkPanel, label='Añadir Enlace')
        addBtn.Bind(wx.EVT_BUTTON, self.addNewLink)

        addLinkBox.Add(lblTitle, flag=wx.RIGHT, border=5)
        addLinkBox.Add(self.txtTitle, proportion=1, flag=wx.RIGHT, border=5)
        addLinkBox.Add(lblUrl, flag=wx.RIGHT, border=5)
        addLinkBox.Add(self.txtUrl, proportion=1, flag=wx.RIGHT, border=5)
        addLinkBox.Add(addBtn)
        self.addLinkPanel.SetSizer(addLinkBox)
        self.addLinkPanel.Hide()

        self.vbox.Add(self.addLinkPanel, flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)

        self.linkList.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.openLink)
        self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)

        self.Centre()
        self.Show()

    def loadLinks(self):
        self.linkList.DeleteAllItems()
        self.urlDict.clear()
        try:
            with open('links.json', 'r') as file:
                links = json.load(file)
                for title, url in links.items():
                    index = self.linkList.InsertItem(self.linkList.GetItemCount(), title)
                    self.urlDict[index] = url
        except (FileNotFoundError, json.JSONDecodeError):
            print("Archivo 'links.json' no encontrado o inválido. Se creará uno nuevo al añadir un enlace.")
            with open('links.json', 'w') as file:
                json.dump({}, file)

    def addNewLink(self, event):
        title = self.txtTitle.GetValue()
        url = self.txtUrl.GetValue()
        if title and url:
            index = self.linkList.InsertItem(self.linkList.GetItemCount(), title)
            self.urlDict[index] = url
            self.saveLinks()
            wx.MessageBox('Enlace añadido', 'Info', wx.OK | wx.ICON_INFORMATION)
            self.loadLinks()

    def openLink(self, event):
        index = event.GetIndex()
        url = self.urlDict.get(index)
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
            url = self.urlDict.get(index)
            self.txtTitle.SetValue(title)
            self.txtUrl.SetValue(url)
            self.saveLinks()
            self.loadLinks()

    def deleteLink(self):
        index = self.linkList.GetFirstSelected()
        if index != -1:
            self.linkList.DeleteItem(index)
            del self.urlDict[index]
            self.saveLinks()

    def saveLinks(self):
        with open('links.json', 'w') as file:
            json.dump(self.urlDict, file)

def start_link_manager():
    app = wx.App(False)
    frame = LinkManager(None, 'Gestor de Enlaces')
    app.MainLoop()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    @script(description='Abre la ventana del gestor de enlaces', gesture='kb:NVDA+alt+l', category='Gestor De Enlaces')
    def script_open_file(self, gesture):
        wx.CallAfter(start_link_manager)