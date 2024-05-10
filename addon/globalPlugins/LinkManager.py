# Gestor de enlaces
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
#Copyright (C) 2024 Ayoub El Bakhti


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

class LinkManager(wx.Dialog):
    def __init__(self, parent, title):
        super(LinkManager, self).__init__(parent, title=title, size=(500, 400))
        self.CenterOnScreen()
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.vbox)

        self.linkList = wx.ListCtrl(self.panel, style=wx.LC_REPORT)
        self.linkList.InsertColumn(0, _('Título'), width=400)
        self.linkList.SetFocus()
        self.links = {}
        self.loadLinks()
        self.vbox.Add(self.linkList, proportion=1, flag=wx.EXPAND)
        #Translators: botón para añadir enlace
        self.btnAddLink = wx.Button(self.panel, label=_("Añadir Enlace"))
        #Translators: botón para editar enlace.
        self.btnEditLink = wx.Button(self.panel, label=_("Editar Enlace"))
        #Translators: borrar enlace
        self.btnDeleteLink = wx.Button(self.panel, label=_("Borrar Enlace"))
        self.btnAddLink.Bind(wx.EVT_BUTTON, self.onContextMenuAddLink)
        self.btnEditLink.Bind(wx.EVT_BUTTON, self.onContextMenuEditLink)
        self.btnDeleteLink.Bind(wx.EVT_BUTTON, self.onContextMenuDeleteLink)
        self.vbox.Add(self.btnAddLink, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=5)
        self.vbox.Add(self.btnEditLink, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=5)
        self.vbox.Add(self.btnDeleteLink, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=5)
        self.addLinkPanel = wx.Panel(self.panel)
        addLinkBox = wx.BoxSizer(wx.HORIZONTAL)
        # Translators: campo para el título del link.
        lblTitle = wx.StaticText(self.addLinkPanel, label=_("Título:"))
        self.txtTitle = wx.TextCtrl(self.addLinkPanel)
        # Translators: panel para la url.
        lblUrl = wx.StaticText(self.addLinkPanel, label=_("URL:"))
        self.txtUrl = wx.TextCtrl(self.addLinkPanel)
        # Translators: botón para guardar.
        self.addBtn = wx.Button(self.addLinkPanel, label=_("&Guardar"))
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
        self.linkList.PopupMenu(self.contextMenu(), self.linkList.GetPosition())

    def contextMenu(self):
        menu=wx.Menu()
        # Translators: Opción para añadir enlaces
        agregarLinkItem = menu.Append(wx.ID_ANY, _("&Añadir un enlace"), _("Añade un link a la lista")) 
        self.Bind(wx.EVT_MENU, self.onContextMenuAddLink, agregarLinkItem)
        # Translators: Opción para editar el enlace
        editarItem = menu.Append(wx.ID_ANY, _("&Editar enlace"), _("Editar item")) 
        self.Bind(wx.EVT_MENU, self.onContextMenuEditLink, editarItem)
        # Translators: Opción para borrar el enlace
        borrarItem=menu.Append(wx.ID_ANY,_("&Borrar enlace"),_("Borrar item")) 
        self.Bind(wx.EVT_MENU, self.onContextMenuDeleteLink, borrarItem) 
        # Translators: Opción para exportar los enlaces
        exportarItem = menu.Append(wx.ID_ANY, _("&Exportar enlaces"), _("Exportar enlaces"))
        self.Bind(wx.EVT_MENU, self.onExportLinks, exportarItem)
        # Translators: Opción para importar los enlaces
        importarItem = menu.Append(wx.ID_ANY, _("&Importar enlaces"), _("Importar enlaces"))
        self.Bind(wx.EVT_MENU, self.onImportLinks, importarItem)
        return menu

    def onContextMenuAddLink(self, event):
        self.toggleAddLinkPanel()

    def onContextMenuEditLink(self, event):
        self.editLink()

    def onContextMenuDeleteLink(self, event):
        self.deleteLink()

    def onImportLinks(self, event):
        wildcard = "JSON (*.json)|*.json"
        dialog = wx.FileDialog(self, "Importar enlaces desde...", wildcard=wildcard, style=wx.FD_OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            import_path = dialog.GetPath()
            try:
                with open(import_path, 'r') as file:
                    imported_links = json.load(file)
                    self.links.update(imported_links)
                    self.saveLinks()
                    self.loadLinks()
                    #Translators: Se anuncia que los enlaces han sido importados correctamente.
                    wx.MessageBox(_("Enlaces importados correctamente."), _("Importación Exitosa"), wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                # Translators: se anuncia que hubo un error al importar los enlaces.
                wx.MessageBox(_("Error al importar los enlaces: {0}").format(str(e)), _("Error"), wx.OK | wx.ICON_ERROR)
        dialog.Destroy()

    def onExportLinks(self, event):
        wildcard = "JSON (*.json)|*.json"
        dialog = wx.FileDialog(self, "Guardar enlace como...", wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dialog.ShowModal() == wx.ID_OK:
            export_path = dialog.GetPath()
            try:
                with open(export_path, 'w') as file:
                    json.dump(self.links, file)
                # Translators: se anuncia que se exportaron los enlaces correctamente.
                wx.MessageBox(_("Enlaces exportados correctamente."), _("Exportación Exitosa"), wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
            
                # Translators: se anuncia que hubo un error al exportar los enlaces.
                wx.MessageBox(_("Error al exportar los enlaces: {0}").format(str(e)), _("Error"), wx.OK | wx.ICON_ERROR)
        dialog.Destroy()

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
            # Translators: se anuncia al usuario que se creará un nuevo archivo si no se encuentra.
            ui.message(_("Archivo no encontrado: {path}. Se creará uno nuevo al añadir un enlace.").format(path=path))
            self.saveLinks()
        except json.JSONDecodeError:
            #Translators: Se anuncia de un error al decodificar el archivo json.
            ui.message(_("Error al decodificar el JSON. Verifica el contenido del archivo."))
            self.saveLinks()

    def saveLinks(self):
        try:
            with open(self.getJsonPath(), 'w') as file:
                json.dump(self.links, file)
        except Exception as e:
            error_message = "Error al guardar los enlaces: {}".format(str(e))
            wx.MessageBox(error_message, "Error", wx.OK | wx.ICON_ERROR)

    def onAddOrEditLink(self, event):
        title = self.txtTitle.GetValue()
        url = self.txtUrl.GetValue()
        if not validateUrl(url):
        #Translators: se anuncia que la url no es válida.
            wx.MessageBox(_("La URL no es válida"), 'Error', wx.OK | wx.ICON_ERROR)
            return 
    
        if self.editingIndex is None:
            if title and url and title not in self.links:
                self.links[title] = url
                self.saveLinks()
                # Translators: se anuncia que se añadió un enlace.
                wx.MessageBox(_("Enlace añadido"), _("Info"), wx.OK | wx.ICON_INFORMATION)
                self.loadLinks()
                self.txtTitle.Clear()
                self.txtUrl.Clear()
            elif title in self.links:
                #Translators: se informa que un enlace con ese título ya existe.
                wx.MessageBox(_("Un enlace con este título ya existe"), 'Error', wx.OK | wx.ICON_ERROR)
        else:
            existing_title = self.linkList.GetItemText(self.editingIndex)
            if title and url:
                if title != existing_title and title in self.links:
                    # Translators: se informa que un enlace con ese título ya existe.
                    wx.MessageBox(_("Un enlace con este título ya existe"), 'Error', wx.OK | wx.ICON_ERROR)
                else:
                    del self.links[existing_title]
                    self.links[title] = url
                    self.saveLinks()
                    #Translators: se informa que el enlace fue actualizado.
                    wx.MessageBox(_("Enlace actualizado"), _("Info"), wx.OK | wx.ICON_INFORMATION)
                    self.txtTitle.Clear()
                    self.txtUrl.Clear()
            self.editingIndex = None
            self.addLinkPanel.Hide()
            self.panel.Layout()
            self.linkList.DeleteAllItems()
            for title, url in self.links.items():
                self.linkList.InsertItem(self.linkList.GetItemCount(), title)
            self.linkList.SetFocus()

    def deleteLink(self):
        index = self.linkList.GetFirstSelected()
        if index != -1:
            title = self.linkList.GetItemText(index)
            if title in self.links:
                dlg = wx.MessageDialog(self, f"¿Estás seguro de que quieres borrar el enlace '{title}'?", "Confirmar",  wx.YES_NO | wx.ICON_QUESTION)
                result = dlg.ShowModal()
                dlg.Destroy()
                if result == wx.ID_YES:
                    del self.links[title]
                    self.saveLinks()
                    # Translators: se informa que el enlace fue borrado.
                    wx.MessageBox(_("Enlace borrado"), _("Info"), wx.OK | wx.ICON_INFORMATION)
                    self.loadLinks()
            self.linkList.DeleteAllItems()
            for title, url in self.links.items():
                self.linkList.InsertItem(self.linkList.GetItemCount(), title)
            self.linkList.SetFocus()

    def openLink(self, event):
        title = self.linkList.GetItemText(event.GetIndex())
        url = self.links.get(title)
        if url:
            # Translators: mensaje mostrado cuando se está abriendo una URL en el navegador.
            ui.message(_("Abriendo URL..."))
            webbrowser.open(url)

    def onKeyPress(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.Close()
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
        super(GlobalPlugin, self).__init__()
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
# Translators: decorador para el script.
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
