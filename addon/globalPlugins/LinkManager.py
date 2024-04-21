#A part of NonVisual Desktop Access (NVDA)
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2024 Ayoub El Bakhti

#añadiremos la traducción  próximamente.

import re
import globalVars
import os
import globalPluginHandler
from scriptHandler import script, getLastScriptRepeatCount
import wx
import webbrowser
import json
import gui
import ui
import api
import addonHandler

try:
    addonHandler.initTranslation();
except addonHandler.AddonError:
    from logHandler import log;
    log.warning('Unable to initialise translations. This may be because the addon is running from NVDA scratchpad.');


def disableInSecureMode(decoratedCls):
    if globalVars.appArgs.secure:
        return globalPluginHandler.GlobalPlugin;
    return decoratedCls;

def validateUrl(url):
    if not url: return False
    regex = re.compile(
        r'^https?://|file://|ftp://'  # protocol...
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return True if regex.search(url) else False

class ListContextMenu(wx.Menu):
	def __init__(self, parent):
		super(ListContextMenu, self).__init__()
		self.parent = parent

		item_addLink = wx.MenuItem(self, wx.ID_ANY, _("Añadir"))
		self.Append(item_addLink)
		self.Bind(wx.EVT_MENU, self.action_addLink, item_addLink)

		item_editLink = wx.MenuItem(self, wx.ID_ANY, _("Editar"))
		self.Append(item_editLink)
		self.Bind(wx.EVT_MENU, self.action_editLink, item_editLink)

		item_removeLink = wx.MenuItem(self, wx.ID_ANY, _("Borrar"))
		self.Append(item_removeLink)
		self.Bind(wx.EVT_MENU, self.action_removeLink, item_removeLink)

	def action_addLink(self, event):
		# Aquí el código para añadir un enlace
		event.Skip()

	def action_editLink(self, event):
		# Aquí el código para editar el enlace
		event.Skip()

	def action_removeLink(self, event):
		# Aquí el código para borrar un enlace
		event.Skip()

class LinkManager(wx.Dialog):
    def __init__(self, parent, title):
        super(LinkManager, self).__init__(parent, title=title, size=(500, 400))
        self.CenterOnScreen()
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.vbox)

        self.linkList = wx.ListCtrl(self.panel, style=wx.LC_REPORT)
        self.linkList.InsertColumn(0, 'Titulo', width=400)
        self.linkList.SetFocus()
        self.links = {}
        self.loadLinks()
        self.vbox.Add(self.linkList, proportion=1, flag=wx.EXPAND)

        self.addLinkPanel = wx.Panel(self.panel)
        addLinkBox = wx.BoxSizer(wx.HORIZONTAL)
        #traductores: campo para el título del link.
        lblTitle = wx.StaticText(self.addLinkPanel, label=_("Título:"))
        self.txtTitle = wx.TextCtrl(self.addLinkPanel)
        #traductores: panel para la url.
        lblUrl = wx.StaticText(self.addLinkPanel, label=_("URL:"))
        self.txtUrl = wx.TextCtrl(self.addLinkPanel)
        #traductores: botón para guardar.
        self.addBtn = wx.Button(self.addLinkPanel, label=_("Guardar"))
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

        self.Bind(wx.EVT_CONTEXT_MENU, self.onListContextMenu, self.linkList)

    def onListContextMenu(self, event):
        self.linkList.PopupMenu(ListContextMenu(self.linkList), self.linkList.GetPosition())

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
            ui.message(_("Archivo no encontrado: {path}. Se creará uno nuevo al añadir un enlace.").format(path=path))
            self.saveLinks()
        except json.JSONDecodeError:
            ui.message(_("Error al decodificar JSON. Verifique el contenido del archivo."))
            self.saveLinks()

    def saveLinks(self):
        with open(self.getJsonPath(), 'w') as file:
            json.dump(self.links, file)

    def onAddOrEditLink(self, event):
        title = self.txtTitle.GetValue()
        url = self.txtUrl.GetValue()
        if not validateUrl(url):
            wx.MessageBox(_("La URL no es válida"), 'Error', wx.OK | wx.ICON_ERROR)
            return 
    
        if self.editingIndex is None:
            if title and url and title not in self.links:
                self.links[title] = url
                self.saveLinks()
                #traductores: se anuncia que se añadió un enlace.
                wx.MessageBox(_("Enlace añadido"), _("Info"), wx.OK | wx.ICON_INFORMATION)
                self.loadLinks()
                self.txtTitle.Clear()
                self.txtUrl.Clear()
            elif title in self.links:
                #Traductores: se informa que un enlace con ese título ya existe.
                wx.MessageBox(_("Un enlace con este título ya existe"), 'Error', wx.OK | wx.ICON_ERROR)
        else:
            existing_title = self.linkList.GetItemText(self.editingIndex)
            if title and url:
                if title != existing_title and title in self.links:
                    #traductores: se informa que un enlace con ese título ya existe.
                    wx.MessageBox(_("Un enlace con este título ya existe"), 'Error', wx.OK | wx.ICON_ERROR)
                else:
                    del self.links[existing_title]
                    self.links[title] = url
                    self.saveLinks()
                    #Traductores: se informa que el enlace fue actualizado.
                    wx.MessageBox(_("Enlace actualizado"), _("Info"), wx.OK | wx.ICON_INFORMATION)
                    self.txtTitle.Clear()
                    self.txtUrl.Clear()
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
                #traductores: se informa que el enlace fue borrado.
                wx.MessageBox(_("Enlace borrado"), _("Info"), wx.OK | wx.ICON_INFORMATION)

    def openLink(self, event):
        title = self.linkList.GetItemText(event.GetIndex())
        url = self.links.get(title)
        if url:
            # Traductores: mensaje mostrado cuando se está abriendo una URL en el navegador.
            ui.message(_("Abriendo URL..."))
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

def saveLinkScript(title,url):
    pathFile=os.path.join(globalVars.appArgs.configPath, "links.json")
    data={}
    try:
        with open(pathFile,'r') as file:
            data=json.load(file)
    except FileNotFoundError:   
        data={}
    data[title]= url
    with open(pathFile,'w') as file:
        json.dump(data,file)

@disableInSecureMode
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self):
        super().__init__()
        self.link_manager = None
        self.addLinkInfo = "", ""

    def create_or_toggle_link_manager(self, addLink=False):
        if not self.link_manager:
            self.link_manager = LinkManager(gui.mainFrame, 'Gestor de Enlaces')
        if self.link_manager.IsShown() and not self.link_manager.IsActive():
            # La ventana se muestra en pantalla pero está minimizada o en segundo plano. Se oculta para a continuación mostrarla de nuevo y así traerla al frente.
            self.link_manager.Hide()
        if not self.link_manager.IsShown():
            gui.mainFrame.prePopup()
            self.link_manager.Show()
            gui.mainFrame.postPopup()
        title, url = self.addLinkInfo
        if addLink and validateUrl(url):
            self.link_manager.addLinkPanel.Show()
            self.link_manager.txtTitle.Clear()
            self.link_manager.txtTitle.SetValue(title if title else _("Sin título"))
            self.link_manager.txtTitle.SetFocus()
            self.link_manager.txtUrl.Clear()
            self.link_manager.txtUrl.SetValue(url)
            # Después de usarla, se resetea
            self.addLinkInfo = "", ""

    def refreshLinkInfo(self):
        title, url = "", ""
        obj = api.getNavigatorObject()
        if not obj.treeInterceptor:
            obj = api.getFocusObject()
        if obj.treeInterceptor:
            root = obj.treeInterceptor.rootNVDAObject
            url = root.IAccessibleObject.accValue(obj.IAccessibleChildID)
            title = root.name
        self.addLinkInfo = title, url

    @script(description=_("Abre la ventana del gestor de enlaces"),
        gesture="kb:NVDA+alt+k",
        category=_("Gestor De Enlaces"))
    def script_open_file(self, gesture):
        addLink = False
        if getLastScriptRepeatCount() == 0:
            # Con la primera pulsación del gesto guardamos la info del enlace si lo hay.
            self.refreshLinkInfo()
        elif getLastScriptRepeatCount() == 1:
            # Con la segunda pulsación ponemos addLink a True para que create_or_toggle_link_manager sepa que si hay una url válida almacenada la tiene que mostrar.
            addLink = True
        wx.CallAfter(self.create_or_toggle_link_manager, addLink)

