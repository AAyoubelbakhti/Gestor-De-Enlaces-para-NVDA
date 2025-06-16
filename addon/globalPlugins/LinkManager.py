#Gestor de enlaces
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
ALL_CATEGORIES = _("Todas las categorías")
UNCATEGORIZED = _("Sin categoría")   

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
        r'^https?://|file://|ftp://'  #protocol...
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  #domain...
        r'localhost|'  #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' #...or ip
        r'(?::\d+)?'  #optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return True if regex.search(url) else False
class CategoryManagerDialog(wx.Dialog):
    def __init__(self, parent, title):
        super(CategoryManagerDialog, self).__init__(parent, title=title, size=(450, 350))
        self.link_manager_ref = parent
        self.panel = wx.Panel(self)
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        list_label = wx.StaticText(self.panel, label=_("Categorías Existentes:"))
        main_sizer.Add(list_label, 0, wx.ALL | wx.EXPAND, 5)

        self.categoryListCtrl = wx.ListCtrl(self.panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_SORT_ASCENDING)
        self.categoryListCtrl.InsertColumn(0, _("Nombre de Categoría"), width=380)
        main_sizer.Add(self.categoryListCtrl, 1, wx.EXPAND | wx.ALL, 5)
        
        self.editPanel = wx.Panel(self.panel)
        edit_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.lblCategoryName = wx.StaticText(self.editPanel, label=_("Nombre:"))
        edit_sizer.Add(self.lblCategoryName, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        self.txtCategoryName = wx.TextCtrl(self.editPanel)
        edit_sizer.Add(self.txtCategoryName, 1, wx.EXPAND | wx.RIGHT, 5)
        
        self.btnSaveCategory = wx.Button(self.editPanel, label=_("&Guardar"))
        self.btnSaveCategory.Bind(wx.EVT_BUTTON, self.onSaveCategory)
        edit_sizer.Add(self.btnSaveCategory, 0, 0, 0)
        
        self.editPanel.SetSizer(edit_sizer)
        self.editPanel.Hide()
        main_sizer.Add(self.editPanel, 0, wx.EXPAND | wx.ALL, 5)

        action_buttons_sizer = wx.StdDialogButtonSizer()

        self.btnAdd = wx.Button(self.panel, label=_("&Añadir Nueva..."))
        self.btnAdd.Bind(wx.EVT_BUTTON, self.onAddNew)
        action_buttons_sizer.AddButton(self.btnAdd)

        self.btnEdit = wx.Button(self.panel, label=_("&Editar Seleccionada..."))
        self.btnEdit.Bind(wx.EVT_BUTTON, self.onEditSelected)
        action_buttons_sizer.AddButton(self.btnEdit)

        self.btnDelete = wx.Button(self.panel, label=_("&Borrar Seleccionada"))
        self.btnDelete.Bind(wx.EVT_BUTTON, self.onDeleteSelected)
        action_buttons_sizer.AddButton(self.btnDelete)
        self.btnClose = wx.Button(self.panel, label=_("Cerrar"), id=wx.ID_CANCEL)
        action_buttons_sizer.AddButton(self.btnClose)
        action_buttons_sizer.Realize()
        main_sizer.Add(action_buttons_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.panel.SetSizer(main_sizer)
        self.populateCategoryList()
        self.CenterOnParent()
        self.editing_category_original_name = None

    def populateCategoryList(self):
        self.categoryListCtrl.DeleteAllItems()
        sorted_user_categories = sorted(list(set(self.link_manager_ref.categories)), key=lambda s: s.lower())

        for cat_name in sorted_user_categories:
            self.categoryListCtrl.InsertItem(self.categoryListCtrl.GetItemCount(), cat_name)
        
        if self.categoryListCtrl.GetItemCount() > 0:
            self.categoryListCtrl.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
            self.categoryListCtrl.EnsureVisible(0)

    def onAddNew(self, event):
        self.editing_category_original_name = None
        self.lblCategoryName.SetLabel(_("Nueva Categoría:"))
        self.txtCategoryName.SetValue("")
        self.txtCategoryName.Enable(True)
        self.btnSaveCategory.Enable(True)
        self.editPanel.Show()
        self.panel.Layout()
        self.txtCategoryName.SetFocus()

    def onEditSelected(self, event):
        selected_index = self.categoryListCtrl.GetFirstSelected()
        if selected_index == -1:
            wx.MessageBox(_("Por favor, selecciona una categoría para editar."), _("Ninguna Selección"), wx.OK | wx.ICON_INFORMATION, self)
            return

        original_name = self.categoryListCtrl.GetItemText(selected_index)
        
        if original_name == UNCATEGORIZED and not self.isUncategorizedEditable():
            wx.MessageBox(_("La categoría '{0}' es especial y no se puede editar directamente.").format(UNCATEGORIZED), _("Acción no permitida"), wx.OK | wx.ICON_WARNING, self)
            return

        self.editing_category_original_name = original_name
        self.lblCategoryName.SetLabel(_("Editar Categoría:"))
        self.txtCategoryName.SetValue(original_name)
        self.txtCategoryName.Enable(True)
        self.btnSaveCategory.Enable(True)
        self.editPanel.Show()
        self.panel.Layout()
        self.txtCategoryName.SetFocus()
        self.txtCategoryName.SelectAll()

    def onSaveCategory(self, event):
        new_name = self.txtCategoryName.GetValue().strip()

        if not new_name:
            wx.MessageBox(_("El nombre de la categoría no puede estar vacío."), _("Entrada Inválida"), wx.OK | wx.ICON_ERROR, self)
            self.txtCategoryName.SetFocus()
            return

        existing_categories_lower = [cat.lower() for cat in self.link_manager_ref.categories]
        if self.editing_category_original_name:
            if new_name.lower() != self.editing_category_original_name.lower() and new_name.lower() in existing_categories_lower:
                wx.MessageBox(_("Ya existe una categoría llamada '{0}'.").format(new_name), _("Nombre Duplicado"), wx.OK | wx.ICON_ERROR, self)
                self.txtCategoryName.SetFocus()
                return
        else:
            if new_name.lower() in existing_categories_lower:
                wx.MessageBox(_("Ya existe una categoría llamada '{0}'.").format(new_name), _("Nombre Duplicado"), wx.OK | wx.ICON_ERROR, self)
                self.txtCategoryName.SetFocus()
                return

        if new_name == UNCATEGORIZED and not self.isUncategorizedEditable() and \
        (not self.editing_category_original_name or self.editing_category_original_name != UNCATEGORIZED):
            wx.MessageBox(_("'{0}' es un nombre de categoría reservado.").format(UNCATEGORIZED), _("Nombre Reservado"), wx.OK | wx.ICON_WARNING, self)
            self.txtCategoryName.SetFocus()
            return

        if self.editing_category_original_name is None:
            self.link_manager_ref.categories.append(new_name)
            ui.message(_("Categoría '{0}' añadida.").format(new_name))
        else:
            try:
                original_index = self.link_manager_ref.categories.index(self.editing_category_original_name)
                self.link_manager_ref.categories[original_index] = new_name
            except ValueError:
                self.link_manager_ref.categories.append(new_name)

            self.updateCategoryInLinks(self.editing_category_original_name, new_name)
            ui.message(_("Categoría '{0}' actualizada a '{1}'.").format(self.editing_category_original_name, new_name))

        self.link_manager_ref.categories.sort(key=lambda s: s.lower())
        self.link_manager_ref.saveLinks()
        self.populateCategoryList()

        self.txtCategoryName.SetValue("")
        self.txtCategoryName.Enable(False)
        self.btnSaveCategory.Enable(False)
        self.editPanel.Hide()
        self.panel.Layout()
        self.editing_category_original_name = None
        self.categoryListCtrl.SetFocus()

    def updateCategoryInLinks(self, old_name, new_name):
        links_changed = False
        for title, link_data in self.link_manager_ref.links.items():
            if "categories" in link_data and isinstance(link_data["categories"], list):
                if old_name in link_data["categories"]:
                    link_data["categories"] = [new_name if cat == old_name else cat for cat in link_data["categories"]]
                    links_changed = True

    def onDeleteSelected(self, event):
        selected_index = self.categoryListCtrl.GetFirstSelected()
        if selected_index == -1:
            wx.MessageBox(_("Por favor, selecciona una categoría para borrar."), _("Ninguna Selección"), wx.OK | wx.ICON_INFORMATION, self)
            return

        category_to_delete = self.categoryListCtrl.GetItemText(selected_index)

        if category_to_delete == UNCATEGORIZED and not self.isUncategorizedEditable():
            wx.MessageBox(_("La categoría '{0}' es especial y no se puede borrar.").format(UNCATEGORIZED), _("Acción no permitida"), wx.OK | wx.ICON_WARNING, self)
            return

        confirm_msg = _("¿Estás seguro de que quieres borrar la categoría '{0}'?\n"
                        "Los enlaces que usen esta categoría pasarán a '{1}'.").format(category_to_delete, UNCATEGORIZED)
        dlg_title = _("Confirmar Borrado")
        
        confirm_dialog = wx.MessageDialog(self, confirm_msg, dlg_title, wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT)
        response = confirm_dialog.ShowModal()
        confirm_dialog.Destroy()

        if response == wx.ID_YES:
            if category_to_delete in self.link_manager_ref.categories:
                self.link_manager_ref.categories.remove(category_to_delete)
            
            links_changed = False
            for title, link_data in self.link_manager_ref.links.items():
                if "categories" in link_data and isinstance(link_data["categories"], list):
                    if category_to_delete in link_data["categories"]:
                        link_data["categories"].remove(category_to_delete)
                        if not link_data["categories"]:
                            link_data["categories"] = [UNCATEGORIZED]
                        links_changed = True
            
            self.link_manager_ref.saveLinks()
            self.populateCategoryList()
            ui.message(_("Categoría '{0}' borrada.").format(category_to_delete))
            
            if self.editing_category_original_name == category_to_delete:
                self.txtCategoryName.SetValue("")
                self.txtCategoryName.Enable(False)
                self.btnSaveCategory.Enable(False)
                self.editPanel.Hide()
                self.panel.Layout()
                self.editing_category_original_name = None
            self.categoryListCtrl.SetFocus()

    def isUncategorizedEditable(self):
        # método auxiliar
        return False

class LinkManager(wx.Dialog):
    def __init__(self, parent, title):
        super(LinkManager, self).__init__(parent, title=title, size=(600, 450))
        self.CenterOnScreen()
        self.panel = wx.Panel(self)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(self.vbox)
        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #Translators: Etiqueta para el ComboBox de filtro de categorías.
        lblFilterCategory = wx.StaticText(self.panel, label=_("Filtrar por:"))
        filter_sizer.Add(lblFilterCategory, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        self.filterCategoryCombo = wx.ComboBox(self.panel, style=wx.CB_READONLY | wx.CB_SORT)
        self.filterCategoryCombo.Bind(wx.EVT_COMBOBOX, self.onFilterCategoryChanged)
        filter_sizer.Add(self.filterCategoryCombo, 1, wx.EXPAND, 0)

        self.vbox.Add(filter_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.linkList = wx.ListCtrl(self.panel, style=wx.LC_REPORT)
        self.linkList.InsertColumn(0, _('Título'), width=350)
        self.linkList.InsertColumn(1, _('Categoría'), width=150)
        self.linkList.SetFocus()
        self.links = {}
        self.categories = []
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
        self.btnManageCategories = wx.Button(self.panel, label=_("Gestionar Categorías..."))
        self.btnManageCategories.Bind(wx.EVT_BUTTON, self.onManageCategories)
        self.addLinkPanel = wx.Panel(self.panel)
        addLinkGBS = wx.GridBagSizer(vgap=5, hgap=5)
        action_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        action_buttons_sizer.Add(self.btnAddLink, 0, wx.RIGHT, 5)
        action_buttons_sizer.Add(self.btnEditLink, 0, wx.RIGHT, 5)
        action_buttons_sizer.Add(self.btnDeleteLink, 0, wx.RIGHT, 5) 
        action_buttons_sizer.Add(self.btnManageCategories, 0, 0, 0) # Añadir al sizer horizontal
        self.vbox.Add(action_buttons_sizer, 0, wx.EXPAND | wx.ALL, 5)

        #Translators: campo para el título del link.
        lblTitle = wx.StaticText(self.addLinkPanel, label=_("Título:"))
        self.txtTitle = wx.TextCtrl(self.addLinkPanel)
        addLinkGBS.Add(lblTitle, pos=(0, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        addLinkGBS.Add(self.txtTitle, pos=(0, 1), span=(1, 2), flag=wx.EXPAND)

        #Translators: panel para la url.
        lblUrl = wx.StaticText(self.addLinkPanel, label=_("URL:"))
        self.txtUrl = wx.TextCtrl(self.addLinkPanel)
        addLinkGBS.Add(lblUrl, pos=(1, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        addLinkGBS.Add(self.txtUrl, pos=(1, 1), span=(1, 2), flag=wx.EXPAND)
        lblLinkCategory = wx.StaticText(self.addLinkPanel, label=_("Categoría:"))

        self.linkCategoryCombo = wx.ComboBox(self.addLinkPanel, style=wx.CB_READONLY | wx.CB_SORT)
        addLinkGBS.Add(lblLinkCategory, pos=(2, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        addLinkGBS.Add(self.linkCategoryCombo, pos=(2, 1), flag=wx.EXPAND | wx.RIGHT, border=5)

        #Translators: botón para guardar.
        self.addBtn = wx.Button(self.addLinkPanel, label=_("&Guardar"))
        self.addBtn.Bind(wx.EVT_BUTTON, self.onAddOrEditLink)
        addLinkGBS.Add(self.addBtn, pos=(2, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        addLinkGBS.AddGrowableCol(1)
        self.addLinkPanel.SetSizer(addLinkGBS)
        self.addLinkPanel.Hide()
        self.vbox.Add(self.addLinkPanel, flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=10)
        self.linkList.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.openLink)
        self.Bind(wx.EVT_CHAR_HOOK, self.onKeyPress)
        self.editingIndex = None 
        self.Centre()
        self.Bind(wx.EVT_CONTEXT_MENU, self.onListContextMenu, self.linkList)
        self._populateCategoryComboBox(self.linkCategoryCombo, include_all_categories_option=False, default_selection=UNCATEGORIZED)
        self._populateCategoryComboBox(self.filterCategoryCombo, include_all_categories_option=True, default_selection=ALL_CATEGORIES)

    def onListContextMenu(self, event):
        self.linkList.PopupMenu(self.contextMenu(), self.linkList.GetPosition())

    def contextMenu(self):
        menu=wx.Menu()
        #Translators: Opción para añadir enlaces
        agregarLinkItem = menu.Append(wx.ID_ANY, _("&Añadir un enlace"), _("Añade un link a la lista")) 
        self.Bind(wx.EVT_MENU, self.onContextMenuAddLink, agregarLinkItem)
        #Translators: Opción para editar el enlace
        editarItem = menu.Append(wx.ID_ANY, _("&Editar enlace"), _("Editar item")) 
        self.Bind(wx.EVT_MENU, self.onContextMenuEditLink, editarItem)
        #Translators: Opción para borrar el enlace
        borrarItem=menu.Append(wx.ID_ANY,_("&Borrar enlace"),_("Borrar item")) 
        self.Bind(wx.EVT_MENU, self.onContextMenuDeleteLink, borrarItem) 
        #Translators: Opción para exportar los enlaces
        exportarItem = menu.Append(wx.ID_ANY, _("&Exportar enlaces"), _("Exportar enlaces"))
        self.Bind(wx.EVT_MENU, self.onExportLinks, exportarItem)
        #Translators: Opción para importar los enlaces
        importarItem = menu.Append(wx.ID_ANY, _("&Importar enlaces"), _("Importar enlaces"))
        self.Bind(wx.EVT_MENU, self.onImportLinks, importarItem)
        manageCategoriesItem = menu.Append(wx.ID_ANY, _("Gestionar Categorías..."), _("Abre el diálogo para gestionar categorías"))
        self.Bind(wx.EVT_MENU, self.onManageCategories, manageCategoriesItem)
        
        return menu

    def onContextMenuAddLink(self, event):
        self.editingIndex = None
        self.toggleAddLinkPanel(is_editing=False)

    def onContextMenuEditLink(self, event):
        self.editLink()

    def onContextMenuDeleteLink(self, event):
        self.deleteLink()

    def _populateCategoryComboBox(self, comboBox, include_all_categories_option=False, default_selection=UNCATEGORIZED):
        current_value = comboBox.GetValue()

        comboBox.Clear()

        if include_all_categories_option:
            comboBox.Append(ALL_CATEGORIES)
        
        comboBox.Append(UNCATEGORIZED)

        for cat_name in self.categories:
            if cat_name != UNCATEGORIZED:
                comboBox.Append(cat_name)
        
        if current_value and comboBox.FindString(current_value) != wx.NOT_FOUND:
            comboBox.SetValue(current_value)
        elif comboBox.FindString(default_selection) != wx.NOT_FOUND:
            comboBox.SetValue(default_selection)
        elif comboBox.GetCount() > 0:
            comboBox.SetSelection(0)

    def onManageCategories(self, event):
        category_dialog = CategoryManagerDialog(self, _("Gestionar Categorías"))
        category_dialog.ShowModal()
        category_dialog.Destroy()
        self._populateCategoryComboBox(self.linkCategoryCombo, include_all_categories_option=False, default_selection=UNCATEGORIZED)
        self._populateCategoryComboBox(self.filterCategoryCombo, include_all_categories_option=True, default_selection=ALL_CATEGORIES)
        self.displayLinks()

    def onImportLinks(self, event):
        wildcard = _("Archivos JSON (*.json)|*.json")
        dialog = wx.FileDialog(self, _("Importar datos desde..."), wildcard=wildcard, style=wx.FD_OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            import_path = dialog.GetPath()
            try:
                with open(import_path, 'r', encoding='utf-8') as file:
                    imported_data_file = json.load(file)

                    imported_user_cats = imported_data_file.get("__user_defined_categories__", [])
                    if isinstance(imported_user_cats, list):
                        for cat_name in imported_user_cats:
                            if cat_name not in self.categories:
                                self.categories.append(cat_name)
                        self.categories.sort(key=lambda s: s.lower())

                    links_imported_count = 0
                    links_updated_count = 0
                    for title, item_data_from_file in imported_data_file.items():
                        if title == "__user_defined_categories__":
                            continue

                        final_link_data_to_import = {}
                        if isinstance(item_data_from_file, str):
                            final_link_data_to_import["url"] = item_data_from_file
                            final_link_data_to_import["categories"] = [UNCATEGORIZED]
                        elif isinstance(item_data_from_file, dict):
                            final_link_data_to_import["url"] = item_data_from_file.get("url", "")
                            cats_list = item_data_from_file.get("categories")
                            if isinstance(cats_list, list) and cats_list:
                                final_link_data_to_import["categories"] = cats_list
                            elif isinstance(cats_list, str) and cats_list:
                                final_link_data_to_import["categories"] = [cats_list]
                            else:
                                final_link_data_to_import["categories"] = [UNCATEGORIZED]
                        else:
                            continue 

                        if not final_link_data_to_import.get("url"):
                            continue

                        if title not in self.links:
                            links_imported_count += 1
                        else:
                            links_updated_count +=1
                        self.links[title] = final_link_data_to_import

                    self.saveLinks()
                    self.displayLinks()

                    message = _("Datos importados. Nuevos enlaces: {0}, Enlaces actualizados: {1}. Lista de categorías fusionada.").format(links_imported_count, links_updated_count)
                    wx.MessageBox(message, _("Importación Exitosa"), wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(_("Error al importar los datos: {0}").format(str(e)), _("Error"), wx.OK | wx.ICON_ERROR)
        dialog.Destroy()

    def onExportLinks(self, event):
        wildcard = _("Archivos JSON (*.json)|*.json")
        dialog = wx.FileDialog(self, _("Exportar datos como..."), wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dialog.ShowModal() == wx.ID_OK:
            export_path = dialog.GetPath()
            try:
                data_to_export = {}
                for title, link_data in self.links.items():
                    data_to_export[title] = link_data
                data_to_export["__user_defined_categories__"] = self.categories

                with open(export_path, 'w', encoding='utf-8') as file:
                    json.dump(data_to_export, file, indent=2, ensure_ascii=False)
                wx.MessageBox(_("Datos (enlaces y categorías) exportados correctamente."), _("Exportación Exitosa"), wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(_("Error al exportar los datos: {0}").format(str(e)), _("Error"), wx.OK | wx.ICON_ERROR)
        dialog.Destroy()

    def getJsonPath(self):
        return os.path.join(globalVars.appArgs.configPath, "links.json")

    def onFilterCategoryChanged(self, event):
        self.displayLinks()


    def displayLinks(self):
        self.linkList.DeleteAllItems()
        selected_filter = ""
        if hasattr(self, 'filterCategoryCombo'):
            selected_filter = self.filterCategoryCombo.GetValue()
        else:
            selected_filter = ALL_CATEGORIES

        sorted_titles = sorted(self.links.keys(), key=lambda k: k.lower())
        for title in sorted_titles:
            link_data = self.links.get(title)

            if not isinstance(link_data, dict) or "url" not in link_data or "categories" not in link_data:
                if selected_filter == ALL_CATEGORIES:
                    index = self.linkList.InsertItem(self.linkList.GetItemCount(), title)
                    self.linkList.SetItem(index, 1, _("Error de datos"))
                continue
            link_actual_categories = link_data.get("categories", [])
            show_this_link = False
            if selected_filter == ALL_CATEGORIES:
                show_this_link = True
            elif selected_filter == UNCATEGORIZED:
                if not link_actual_categories or link_actual_categories == [UNCATEGORIZED]:
                    show_this_link = True
            else:
                if selected_filter in link_actual_categories:
                    show_this_link = True
            if show_this_link:
                categories_to_display_in_list_col = UNCATEGORIZED
                if link_actual_categories and link_actual_categories != [UNCATEGORIZED]:
                    categories_to_display_in_list_col = ", ".join(link_actual_categories)
                
                index = self.linkList.InsertItem(self.linkList.GetItemCount(), title)
                self.linkList.SetItem(index, 1, categories_to_display_in_list_col)


    def loadLinks(self):
        self.links.clear()
        self.categories = []
        path = self.getJsonPath()
        try:
            with open(path, 'r', encoding='utf-8') as file:
                data_from_file = json.load(file)
                self.categories = data_from_file.get("__user_defined_categories__", [])
                if not isinstance(self.categories, list):
                    self.categories = []
                self.categories.sort(key=lambda s: s.lower())
                for title, item_data_in_file in data_from_file.items():
                    if title == "__user_defined_categories__":
                        continue
                    final_link_data = {}
                    if isinstance(item_data_in_file, str):
                        final_link_data["url"] = item_data_in_file
                        final_link_data["categories"] = [UNCATEGORIZED]
                    elif isinstance(item_data_in_file, dict):
                        final_link_data["url"] = item_data_in_file.get("url", "")
                        cats_from_file = item_data_in_file.get("categories")
                        if isinstance(cats_from_file, list) and cats_from_file:
                            final_link_data["categories"] = cats_from_file
                        elif isinstance(cats_from_file, str):
                            final_link_data["categories"] = [cats_from_file] if cats_from_file else [UNCATEGORIZED]
                        else:
                            final_link_data["categories"] = [UNCATEGORIZED]
                    else:
                        continue
                    if not final_link_data.get("url"):
                        continue
                    self.links[title] = final_link_data
        except FileNotFoundError:
            ui.message(_("Archivo no encontrado: {path}. Se creará uno nuevo al añadir un enlace.").format(path=path))
        except json.JSONDecodeError:
            ui.message(_("Error al decodificar el JSON en {path}. Verifica el contenido del archivo.").format(path=path))
            self.links.clear()
            self.categories = []
        except Exception as e: 
            ui.message(_("Error general al cargar datos desde {path}: {error}").format(path=path, error=str(e)))
            self.links.clear()
            self.categories = []
        if hasattr(self, 'linkCategoryCombo'):
            self._populateCategoryComboBox(self.linkCategoryCombo, include_all_categories_option=False, default_selection=UNCATEGORIZED)
        if hasattr(self, 'filterCategoryCombo'):
            self._populateCategoryComboBox(self.filterCategoryCombo, include_all_categories_option=True, default_selection=ALL_CATEGORIES)
        self.displayLinks()

    def saveLinks(self):
        data_to_save = {}
        
        for title, link_data_internal in self.links.items():
            if isinstance(link_data_internal, dict) and \
            "url" in link_data_internal and \
            "categories" in link_data_internal:
                data_to_save[title] = link_data_internal

        data_to_save["__user_defined_categories__"] = self.categories
        
        try:
            with open(self.getJsonPath(), 'w', encoding='utf-8') as file:
                json.dump(data_to_save, file, indent=2, ensure_ascii=False)
        except Exception as e:
            error_message = _("Error al guardar los datos: {0}").format(str(e))
            wx.MessageBox(error_message, _("Error"), wx.OK | wx.ICON_ERROR)


    def onAddOrEditLink(self, event):
        title = self.txtTitle.GetValue().strip()
        url = self.txtUrl.GetValue().strip()
        selected_category_display_name = self.linkCategoryCombo.GetValue()

        link_categories_to_save = [selected_category_display_name]

        if not title:
            wx.MessageBox(_("El título no puede estar vacío."), _('Error'), wx.OK | wx.ICON_ERROR, self)
            self.txtTitle.SetFocus()
            return
        if not validateUrl(url):
            wx.MessageBox(_("La URL no es válida."), _('Error'), wx.OK | wx.ICON_ERROR, self)
            self.txtUrl.SetFocus()
            return

        if self.editingIndex is None:
            if title in self.links:
                wx.MessageBox(_("Un enlace con este título ya existe."), _('Error'), wx.OK | wx.ICON_ERROR, self)
                return
            
            self.links[title] = {"url": url, "categories": link_categories_to_save}
            self.saveLinks()
            wx.MessageBox(_("Enlace '{0}' añadido a la categoría '{1}'.").format(title, selected_category_display_name), _("Info"), wx.OK | wx.ICON_INFORMATION)
            self.txtTitle.Clear()
            self.txtUrl.Clear()
            self.linkCategoryCombo.SetValue(UNCATEGORIZED)
        else:
            original_title_in_list = self.linkList.GetItemText(self.editingIndex)

            if title != original_title_in_list and title in self.links:
                wx.MessageBox(_("Un enlace con el nuevo título '{0}' ya existe.").format(title), _('Error'), wx.OK | wx.ICON_ERROR, self)
                self.txtTitle.SetFocus()
                return

            if title != original_title_in_list:
                if original_title_in_list in self.links:
                    del self.links[original_title_in_list]

            self.links[title] = {"url": url, "categories": link_categories_to_save}
            self.saveLinks()
            wx.MessageBox(_("Enlace '{0}' actualizado. Categoría: '{1}'.").format(title, selected_category_display_name), _("Info"), wx.OK | wx.ICON_INFORMATION)
            self.txtTitle.Clear()
            self.txtUrl.Clear()
            self.linkCategoryCombo.SetValue(UNCATEGORIZED)

        self.editingIndex = None
        if self.addLinkPanel.IsShown():
            self.addLinkPanel.Hide()
            self.panel.Layout()

        self.displayLinks()
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
                    #Translators: se informa que el enlace fue borrado.
                    wx.MessageBox(_("Enlace borrado"), _("Info"), wx.OK | wx.ICON_INFORMATION)
                    self.displayLinks()
            self.linkList.SetFocus()

    def openLink(self, event):
        index = event.GetIndex()
        title = self.linkList.GetItemText(index)
        link_data = self.links.get(title)
        if isinstance(link_data, dict) and "url" in link_data:
            url_to_open = link_data.get("url")
            if url_to_open:
                ui.message(_("Abriendo URL"))
                webbrowser.open(url_to_open)
            else:
                ui.message(_("El enlace '{0}' no tiene una URL definida.").format(title))
        else:
            ui.message(_("No se pudieron encontrar los datos de la URL para '{0}'.").format(title))

    def onKeyPress(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.Close()
        if event.ControlDown() and keycode == ord('A'):
            self.toggleAddLinkPanel()
        elif event.ControlDown() and keycode == ord('E'):
            if self.addLinkPanel.IsShown() and self.editingIndex is not None:
                self.addLinkPanel.Hide()
                self.panel.Layout()
                self.linkList.SetFocus()
                self.editingIndex = None
            else:
                self.editLink()
        elif event.ControlDown() and keycode == ord('G'):
                if self.addLinkPanel.IsShown():
                    self.onAddOrEditLink(None)
        elif event.ControlDown() and keycode == ord('B'):
            self.deleteLink()
        elif event.ControlDown() and keycode == ord('C'):
            self.copyLinkToClipboard()
        elif event.ControlDown() and keycode == ord('R'):
            self.reorderLinks() 
        event.Skip()

    def reorderLinks(self):
        self.links = dict(sorted(self.links.items(), key=lambda item: item[0].lower()))
        self.saveLinks()
        self.displayLinks() 
        #Translators: Mensaje de ordenación alfabética
        ui.message(_("Enlaces ordenados alfabéticamente"))


    def copyLinkToClipboard(self):
        index = self.linkList.GetFirstSelected()
        if index != -1:
            title = self.linkList.GetItemText(index)
            link_data = self.links.get(title)

            if isinstance(link_data, dict) and "url" in link_data:
                url_to_copy = link_data.get("url")
                if url_to_copy:
                    if wx.TheClipboard.Open():
                        wx.TheClipboard.SetData(wx.TextDataObject(url_to_copy))
                        wx.TheClipboard.Close()
                        ui.message(_("Enlace para '{0}' copiado al portapapeles.").format(title)) 
                    else:
                        wx.MessageBox(_("No se pudo abrir el portapapeles."), _("Error"), wx.OK | wx.ICON_ERROR)
                else:
                    ui.message(_("El enlace '{0}' no tiene URL para copiar.").format(title))
            else:
                ui.message(_("No se encontraron datos de enlace para '{0}'.").format(title))

    def toggleAddLinkPanel(self, is_editing=False):
        self._populateCategoryComboBox(self.linkCategoryCombo, include_all_categories_option=False, default_selection=UNCATEGORIZED)
        if self.addLinkPanel.IsShown() and not is_editing:
            self.addLinkPanel.Hide()
            self.linkList.SetFocus()
        else:
            if not is_editing:
                self.txtTitle.Clear()
                self.txtUrl.Clear()
                self.linkCategoryCombo.SetValue(UNCATEGORIZED)
                self.editingIndex = None
            if not self.addLinkPanel.IsShown():
                self.addLinkPanel.Show()
            self.txtTitle.SetFocus()
        self.panel.Layout()

    def editLink(self):
        index = self.linkList.GetFirstSelected()
        if index != -1:
            title = self.linkList.GetItemText(index)
            link_data = self.links.get(title)
            if isinstance(link_data, dict) and "url" in link_data:
                self.txtTitle.SetValue(title)
                self.txtUrl.SetValue(link_data.get("url", "")) 
                self._populateCategoryComboBox(self.linkCategoryCombo, include_all_categories_option=False, default_selection=UNCATEGORIZED)
                current_link_categories = link_data.get("categories", [UNCATEGORIZED])
                category_to_select_in_combo = UNCATEGORIZED
                if current_link_categories:
                    category_to_select_in_combo = current_link_categories[0]
                
                if self.linkCategoryCombo.FindString(category_to_select_in_combo) != wx.NOT_FOUND:
                    self.linkCategoryCombo.SetValue(category_to_select_in_combo)
                else:
                    self.linkCategoryCombo.SetValue(UNCATEGORIZED)

                self.editingIndex = index
                self.toggleAddLinkPanel(is_editing=True) 


def saveLinkScript(title, url, category_name=None):
    pathFile = os.path.join(globalVars.appArgs.configPath, "links.json")
    data_file_content = {}
    try:
        with open(pathFile, 'r', encoding='utf-8') as file:
            data_file_content = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data_file_content = {"__user_defined_categories__": []}

    user_cats_list = data_file_content.get("__user_defined_categories__", [])
    if not isinstance(user_cats_list, list):
        user_cats_list = []

    link_categories_to_save = []
    if category_name:
        link_categories_to_save = [category_name]
        if category_name not in user_cats_list:
            user_cats_list.append(category_name)
            user_cats_list.sort(key=lambda s: s.lower())
    else:
        link_categories_to_save = [UNCATEGORIZED]

    data_file_content["__user_defined_categories__"] = user_cats_list
    data_file_content[title] = {"url": url, "categories": link_categories_to_save}

    try:
        with open(pathFile, 'w', encoding='utf-8') as file:
            json.dump(data_file_content, file, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error en saveLinkScript al guardar el enlace '{title}': {e}")

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
            #La ventana se muestra en pantalla pero está minimizada o en segundo plano. Se oculta para a continuación mostrarla de nuevo y así traerla al frente.
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
            #Después de usarla, se resetea
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
#Translators: decorador para el script.
    @script(description=_("Abre la ventana del gestor de enlaces"),
        gesture="kb:NVDA+alt+k",
        category=_("Gestor De Enlaces"))
    def script_open_file(self, gesture):
        addLink = False
        if getLastScriptRepeatCount() == 0:
            #Con la primera pulsación del gesto guardamos la info del enlace si lo hay.
            self.refreshLinkInfo()
        elif getLastScriptRepeatCount() == 1:
            #Con la segunda pulsación ponemos addLink a True para que create_or_toggle_link_manager sepa que si hay una url válida almacenada la tiene que mostrar.
            addLink = True
        wx.CallAfter(self.create_or_toggle_link_manager, addLink)
