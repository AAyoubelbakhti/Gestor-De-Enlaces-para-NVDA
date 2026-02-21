# -*- coding: utf-8 -*-
# Gestor de enlaces - Módulo de diálogos
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2024 Ayoub El Bakhti

import os
import re
import shutil
import threading
import webbrowser
import wx
import gui
import ui
import speech
from time import sleep
import addonHandler

addonHandler.initTranslation()

# Translators: Nombre de la categoría por defecto.
UNCATEGORIZED = _("Sin categoría")
# Translators: Etiqueta para mostrar todas las categorías.
ALL_CATEGORIES = _("Todas las categorías")


def validateInput(value):
	if not value:
		return False, 'invalid'
	url_pattern = re.compile(
		r'^(https?://|ftp://|file://|www\.)'
		r'|'
		r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$',
		re.IGNORECASE
	)
	if url_pattern.search(value):
		return True, 'url'
	if os.path.exists(value):
		return True, 'path'
	return False, 'invalid'


def mute(time, msg=False):
	if msg:
		ui.message(msg)
		sleep(0.1)
	threading.Thread(target=_killSpeak, args=(time,), daemon=True).start()


def _killSpeak(time):
	if speech.getState().speechMode != speech.SpeechMode.talk:
		return
	speech.setSpeechMode(speech.SpeechMode.off)
	sleep(time)
	speech.setSpeechMode(speech.SpeechMode.talk)


class CategoryManagerDialog(wx.Dialog):
	def __init__(self, parent, title, db_manager):
		super(CategoryManagerDialog, self).__init__(parent, title=title, size=(450, 350))
		self.db_manager = db_manager
		self.create_widgets()
		self.bind_events()
		self.populate_categories()
		self.CenterOnParent()

	def create_widgets(self):
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		# Translators: Etiqueta de la lista de categorías.
		list_label = wx.StaticText(self, label=_("Categorías:"))
		main_sizer.Add(list_label, 0, wx.ALL | wx.EXPAND, 5)
		self.list_ctrl = wx.ListBox(self)
		main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 5)
		btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Botón para añadir categoría.
		self.btn_add = wx.Button(self, label=_("&Añadir..."))
		# Translators: Botón para renombrar categoría.
		self.btn_edit = wx.Button(self, label=_("&Renombrar..."))
		# Translators: Botón para eliminar categoría.
		self.btn_delete = wx.Button(self, label=_("&Eliminar"))
		btn_sizer.Add(self.btn_add, 1, wx.EXPAND | wx.RIGHT, 5)
		btn_sizer.Add(self.btn_edit, 1, wx.EXPAND | wx.RIGHT, 5)
		btn_sizer.Add(self.btn_delete, 1, wx.EXPAND)
		main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
		# Translators: Botón para cerrar el diálogo.
		close_btn = self.CreateStdDialogButtonSizer(wx.CLOSE)
		main_sizer.Add(close_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
		self.SetSizer(main_sizer)

	def bind_events(self):
		self.btn_add.Bind(wx.EVT_BUTTON, self.on_add)
		self.btn_edit.Bind(wx.EVT_BUTTON, self.on_edit)
		self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)

	def populate_categories(self):
		self.list_ctrl.Clear()
		categories = [cat for cat in self.db_manager.get_all_categories() if cat != UNCATEGORIZED]
		self.list_ctrl.AppendItems(categories)

	def on_add(self, event):
		# Translators: Título del diálogo para nueva categoría.
		with wx.TextEntryDialog(self, _("Nombre de la nueva categoría:"), _("Añadir Categoría")) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				new_name = dlg.GetValue().strip()
				if new_name and new_name != UNCATEGORIZED:
					self.db_manager.add_category(new_name)
					self.populate_categories()
					# Translators: Mensaje al añadir categoría.
					mute(0.3, _("Categoría '{0}' añadida.").format(new_name))

	def on_edit(self, event):
		selected = self.list_ctrl.GetStringSelection()
		if not selected:
			return
		# Translators: Título del diálogo para renombrar categoría.
		with wx.TextEntryDialog(self, _("Renombrar categoría '{0}' a:").format(selected), _("Renombrar Categoría"), value=selected) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				new_name = dlg.GetValue().strip()
				if new_name and new_name != selected and new_name != UNCATEGORIZED:
					self.db_manager.rename_category(selected, new_name)
					self.populate_categories()
					# Translators: Mensaje al renombrar categoría.
					mute(0.3, _("Categoría '{0}' renombrada a '{1}'.").format(selected, new_name))

	def on_delete(self, event):
		selected = self.list_ctrl.GetStringSelection()
		if not selected:
			return
		# Translators: Confirmación de borrado de categoría.
		if wx.MessageBox(
			_("¿Borrar la categoría '{0}'? Los elementos pasarán a '{1}'.").format(selected, UNCATEGORIZED),
			_("Confirmar"), wx.YES_NO | wx.ICON_QUESTION
		) == wx.YES:
			self.db_manager.delete_category(selected, UNCATEGORIZED)
			self.populate_categories()
			# Translators: Mensaje al borrar categoría.
			mute(0.3, _("Categoría '{0}' borrada.").format(selected))


class AddEditDialog(wx.Dialog):
	def __init__(self, parent, title, db_manager, item_title=None):
		super(AddEditDialog, self).__init__(parent, title=title)
		self.db_manager = db_manager
		self.item_title = item_title
		self.item_data = self.db_manager.get_item_by_title(item_title) if item_title else None
		self.create_widgets()
		self.bind_events()
		self.populate_fields()
		self.GetSizer().Fit(self)
		self.CenterOnParent()

	def create_widgets(self):
		main_sizer = wx.BoxSizer(wx.VERTICAL)
		grid_sizer = wx.GridBagSizer(vgap=5, hgap=5)

		# Translators: Etiqueta para el campo de título.
		lblTitle = wx.StaticText(self, label=_("Título:"))
		self.txtTitle = wx.TextCtrl(self)
		grid_sizer.Add(lblTitle, pos=(0, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
		grid_sizer.Add(self.txtTitle, pos=(0, 1), flag=wx.EXPAND)

		# Translators: Etiqueta para el campo de valor (URL o ruta).
		lblValue = wx.StaticText(self, label=_("Valor (URL o Ruta):"))
		self.txtValue = wx.TextCtrl(self)
		grid_sizer.Add(lblValue, pos=(1, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
		grid_sizer.Add(self.txtValue, pos=(1, 1), flag=wx.EXPAND)

		# Translators: Etiqueta para el selector de categoría.
		lblItemCategory = wx.StaticText(self, label=_("Categoría:"))
		self.itemCategoryCombo = wx.ComboBox(self, style=wx.CB_SORT)
		# Translators: Botón para gestionar categorías.
		self.btnManageCategories = wx.Button(self, label=_("Gestionar..."))
		cat_sizer = wx.BoxSizer(wx.HORIZONTAL)
		cat_sizer.Add(self.itemCategoryCombo, 1, wx.EXPAND | wx.RIGHT, 5)
		cat_sizer.Add(self.btnManageCategories, 0)
		grid_sizer.Add(lblItemCategory, pos=(2, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
		grid_sizer.Add(cat_sizer, pos=(2, 1), flag=wx.EXPAND)

		grid_sizer.AddGrowableCol(1)
		main_sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 10)
		btn_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
		main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
		self.SetSizer(main_sizer)

	def bind_events(self):
		self.Bind(wx.EVT_BUTTON, self.on_save, id=wx.ID_OK)
		self.btnManageCategories.Bind(wx.EVT_BUTTON, self.on_manage_categories)

	def populate_fields(self):
		self.itemCategoryCombo.Clear()
		categories = self.db_manager.get_all_categories()
		if UNCATEGORIZED not in categories:
			categories.insert(0, UNCATEGORIZED)
		self.itemCategoryCombo.AppendItems(categories)
		if self.item_data:
			self.txtTitle.SetValue(self.item_data[0])
			self.txtValue.SetValue(self.item_data[1])
			self.itemCategoryCombo.SetValue(self.item_data[3] or UNCATEGORIZED)
		else:
			self.itemCategoryCombo.SetValue(UNCATEGORIZED)

	def on_manage_categories(self, event):
		with CategoryManagerDialog(self, _("Gestionar Categorías"), self.db_manager) as dlg:
			dlg.ShowModal()
		self.populate_fields()

	def on_save(self, event):
		title = self.txtTitle.GetValue().strip()
		value = self.txtValue.GetValue().strip().strip('"')
		category = self.itemCategoryCombo.GetValue().strip()
		if not category:
			category = UNCATEGORIZED
		if not title or not value:
			# Translators: Error cuando el título o valor están vacíos.
			wx.MessageBox(_("El título y el valor no pueden estar vacíos."), _('Error'), wx.OK | wx.ICON_ERROR, self)
			return
		is_valid, item_type = validateInput(value)
		if not is_valid:
			# Translators: Error cuando el valor no es URL ni ruta válida.
			wx.MessageBox(_("El valor no es una URL o ruta válida."), _('Error'), wx.OK | wx.ICON_ERROR, self)
			return
		if not self.item_title and self.db_manager.get_item_by_title(title):
			# Translators: Error cuando ya existe un elemento con ese título.
			wx.MessageBox(_("Un elemento con este título ya existe."), _('Error'), wx.OK | wx.ICON_ERROR, self)
			return
		event.Skip()

	def get_item_data(self):
		title = self.txtTitle.GetValue().strip()
		value = self.txtValue.GetValue().strip().strip('"')
		category = self.itemCategoryCombo.GetValue().strip()
		if not category:
			category = UNCATEGORIZED
		_is_valid, item_type = validateInput(value)
		return title, value, item_type, category


class SettingsDialog(wx.Dialog):
	def __init__(self, parent, title, db_manager, db_path):
		super(SettingsDialog, self).__init__(parent, title=title)
		self.db_manager = db_manager
		self.db_path = db_path
		self.create_widgets()
		self.bind_events()
		self.populate_fields()
		self.GetSizer().Fit(self)
		self.CenterOnParent()

	def create_widgets(self):
		main_sizer = wx.BoxSizer(wx.VERTICAL)

		# Translators: Título de la sección General en configuración.
		general_box = wx.StaticBox(self, label=_("General"))
		general_sizer = wx.StaticBoxSizer(general_box, wx.VERTICAL)
		# Translators: Checkbox para pedir confirmación al borrar.
		self.confirm_delete_checkbox = wx.CheckBox(self, label=_("Pedir confirmación al borrar un elemento"))
		general_sizer.Add(self.confirm_delete_checkbox, 0, wx.ALL, 5)
		main_sizer.Add(general_sizer, 0, wx.EXPAND | wx.ALL, 5)

		# Translators: Título de la sección Categorías.
		cat_box = wx.StaticBox(self, label=_("Categorías"))
		cat_sizer = wx.StaticBoxSizer(cat_box, wx.VERTICAL)
		# Translators: Botón para gestionar categorías desde configuración.
		self.btn_manage_categories = wx.Button(self, label=_("Gestionar Categorías..."))
		cat_sizer.Add(self.btn_manage_categories, 0, wx.EXPAND | wx.ALL, 5)
		main_sizer.Add(cat_sizer, 0, wx.EXPAND | wx.ALL, 5)

		# Translators: Título de la sección Gestión de Datos.
		data_box = wx.StaticBox(self, label=_("Gestión de Datos"))
		data_sizer = wx.StaticBoxSizer(data_box, wx.VERTICAL)
		backup_btns_sizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Botón para crear copia de seguridad.
		self.btn_export = wx.Button(self, label=_("Crear Copia de Seguridad..."))
		# Translators: Botón para restaurar copia de seguridad.
		self.btn_import = wx.Button(self, label=_("Restaurar Copia..."))
		backup_btns_sizer.Add(self.btn_export, 1, wx.EXPAND | wx.RIGHT, 5)
		backup_btns_sizer.Add(self.btn_import, 1, wx.EXPAND)
		data_sizer.Add(backup_btns_sizer, 0, wx.EXPAND | wx.ALL, 5)
		# Translators: Botón para migrar datos desde JSON antiguo.
		self.btn_migrate = wx.Button(self, label=_("Migrar desde JSON Antiguo..."))
		data_sizer.Add(self.btn_migrate, 0, wx.EXPAND | wx.ALL, 5)
		# Translators: Botón para borrar la base de datos.
		self.btn_delete_db = wx.Button(self, label=_("Borrar Base de Datos..."))
		data_sizer.Add(self.btn_delete_db, 0, wx.EXPAND | wx.ALL, 5)
		main_sizer.Add(data_sizer, 0, wx.EXPAND | wx.ALL, 5)

		btn_sizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
		main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
		self.SetSizer(main_sizer)

	def bind_events(self):
		self.Bind(wx.EVT_BUTTON, self.on_save, id=wx.ID_OK)
		self.btn_manage_categories.Bind(wx.EVT_BUTTON, self.on_manage_categories)
		self.btn_export.Bind(wx.EVT_BUTTON, self.on_export)
		self.btn_import.Bind(wx.EVT_BUTTON, self.on_import)
		self.btn_migrate.Bind(wx.EVT_BUTTON, self.on_migrate)
		self.btn_delete_db.Bind(wx.EVT_BUTTON, self.on_delete_db)

	def populate_fields(self):
		self.confirm_delete_checkbox.SetValue(
			self.db_manager.get_setting("confirm_on_delete", "1") == "1"
		)

	def on_save(self, event):
		self.db_manager.set_setting(
			"confirm_on_delete",
			"1" if self.confirm_delete_checkbox.IsChecked() else "0"
		)
		event.Skip()

	def on_manage_categories(self, event):
		with CategoryManagerDialog(self, _("Gestionar Categorías"), self.db_manager) as dlg:
			dlg.ShowModal()
		self.GetParent().display_items()

	def on_export(self, event):
		# Translators: Título del diálogo para guardar copia de seguridad.
		with wx.FileDialog(
			self, _("Guardar copia de seguridad"),
			wildcard=_("Archivo de Base de Datos (*.db)|*.db"),
			defaultFile="gestor_enlaces_backup.db",
			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
		) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				try:
					shutil.copy2(self.db_path, dlg.GetPath())
					# Translators: Mensaje de éxito al guardar copia de seguridad.
					mute(0.3, _("Copia de seguridad guardada."))
				except Exception as e:
					# Translators: Mensaje de error al exportar.
					wx.MessageBox(
						_("Error: {0}").format(str(e)), _("Error"), wx.OK | wx.ICON_ERROR
					)

	def on_import(self, event):
		# Translators: Confirmación antes de restaurar copia de seguridad.
		msg = _("Esto fusionará los datos de la copia de seguridad con tu base de datos actual. ¿Continuar?")
		if wx.MessageBox(msg, _("Aviso de Restauración"), wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
			return
		with wx.FileDialog(
			self, _("Importar copia de seguridad"),
			wildcard=_("Archivo de Base de Datos (*.db)|*.db"),
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
		) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				source_path = dlg.GetPath()
				self.btn_import.Disable()
				thread = threading.Thread(target=self._perform_import, args=(source_path,))
				thread.start()

	def _perform_import(self, source_path):
		try:
			data = self.db_manager.read_data_from_backup(source_path)
			wx.CallAfter(self._finish_import, data)
		except Exception as e:
			wx.CallAfter(self._on_import_error, str(e))

	def _finish_import(self, data):
		try:
			self.db_manager.merge_data_from_backup(data)
			self._on_import_success()
		except Exception as e:
			self._on_import_error(str(e))

	def _on_import_success(self):
		self.btn_import.Enable()
		# Translators: Mensaje de éxito al importar copia de seguridad.
		mute(0.3, _("Importación completada con éxito."))
		self.GetParent().display_items()

	def _on_import_error(self, error_msg):
		self.btn_import.Enable()
		# Translators: Mensaje de error al importar copia de seguridad.
		wx.MessageBox(
			_("Error durante la importación: {0}").format(error_msg), _("Error"), wx.OK | wx.ICON_ERROR
		)

	def on_migrate(self, event):
		# Translators: Confirmación antes de migrar desde JSON.
		msg = _("Esto fusionará los datos del archivo JSON con la base de datos. ¿Continuar?")
		if wx.MessageBox(msg, _("Aviso de Migración"), wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
			return
		# Translators: Título del diálogo para seleccionar JSON.
		with wx.FileDialog(
			self, _("Seleccionar archivo JSON para migrar"),
			wildcard=_("Archivos JSON (*.json)|*.json"),
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
		) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				try:
					rows_added = self.db_manager.migrate_from_json(dlg.GetPath())
					# Translators: Mensaje de éxito de migración.
					mute(0.3, _("{0} nuevos elementos migrados.").format(rows_added))
					self.GetParent().display_items()
				except Exception as e:
					wx.MessageBox(
						_("Error al migrar datos: {0}").format(str(e)),
						_("Error"), wx.OK | wx.ICON_ERROR
					)

	def on_delete_db(self, event):
		# Translators: Advertencia antes de borrar la base de datos.
		msg = _("¡ADVERTENCIA! Esto borrará todos los elementos, categorías y configuraciones. ¿Estás seguro?")
		if wx.MessageBox(msg, _("Confirmación Final Requerida"), wx.YES_NO | wx.ICON_ERROR) != wx.YES:
			return
		try:
			self.db_manager.clear_all_data()
			# Translators: Mensaje de éxito al borrar base de datos.
			mute(0.3, _("Todos los datos han sido eliminados."))
			self.GetParent().display_items()
		except Exception as e:
			wx.MessageBox(
				_("Error: {0}").format(str(e)), _("Error"), wx.OK | wx.ICON_ERROR
			)


class LinkManager(wx.Dialog):
	def __init__(self, parent, title, db_manager, db_path):
		super(LinkManager, self).__init__(parent, title=title, size=(600, 500))
		self.db_manager = db_manager
		self.db_path = db_path
		self.create_widgets()
		self.bind_events()
		self.display_items()
		self.restore_focus()
		self.CenterOnScreen()

	def create_widgets(self):
		self.panel = wx.Panel(self)
		main_sizer = wx.BoxSizer(wx.VERTICAL)

		search_sizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Etiqueta del campo de búsqueda.
		search_label = wx.StaticText(self.panel, label=_("Buscar:"))
		search_sizer.Add(search_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		self.search_ctrl = wx.TextCtrl(self.panel)
		search_sizer.Add(self.search_ctrl, 1, wx.EXPAND)
		main_sizer.Add(search_sizer, 0, wx.EXPAND | wx.ALL, 5)

		self.controls_sizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Etiqueta del selector de filtro.
		filter_label = wx.StaticText(self.panel, label=_("Filtrar:"))
		self.controls_sizer.Add(filter_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		# Translators: Opciones de filtro.
		self.filter_choice = wx.Choice(self.panel, choices=[
			_("Todos"), _("Enlaces"), _("Rutas"), _("Por Categoría")
		])
		self.controls_sizer.Add(self.filter_choice, 1, wx.EXPAND | wx.RIGHT, 5)

		# Translators: Etiqueta del selector de categoría.
		self.category_filter_label = wx.StaticText(self.panel, label=_("Categoría:"))
		self.controls_sizer.Add(self.category_filter_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		self.category_filter_choice = wx.Choice(self.panel)
		self.controls_sizer.Add(self.category_filter_choice, 1, wx.EXPAND | wx.RIGHT, 10)
		self.category_filter_label.Hide()
		self.category_filter_choice.Hide()

		# Translators: Etiqueta del selector de ordenación.
		sort_label = wx.StaticText(self.panel, label=_("Ordenar por:"))
		self.controls_sizer.Add(sort_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
		# Translators: Opciones de ordenación.
		self.sort_choice = wx.Choice(self.panel, choices=[
			_("Alfabéticamente (A-Z)"), _("Alfabéticamente (Z-A)"),
			_("Más recientes primero"), _("Más antiguos primero"),
			_("Más usados"), _("Categoría (A-Z)"), _("Categoría (Z-A)")
		])
		self.controls_sizer.Add(self.sort_choice, 1, wx.EXPAND)
		main_sizer.Add(self.controls_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

		self.itemList = wx.ListCtrl(self.panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
		# Translators: Columna de título en la lista de elementos.
		self.itemList.InsertColumn(0, _('Título'), width=350)
		# Translators: Columna de categoría en la lista de elementos.
		self.itemList.InsertColumn(1, _('Categoría'), width=150)
		main_sizer.Add(self.itemList, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

		action_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Botón para añadir elemento.
		self.btnAddItem = wx.Button(self.panel, label=_("&Añadir..."))
		# Translators: Botón para editar elemento.
		self.btnEditItem = wx.Button(self.panel, label=_("&Editar..."))
		# Translators: Botón para borrar elemento.
		self.btnDeleteItem = wx.Button(self.panel, label=_("&Borrar"))
		# Translators: Botón para abrir configuración.
		self.btnSettings = wx.Button(self.panel, label=_("&Configuración..."))
		action_buttons_sizer.Add(self.btnAddItem, 1, wx.EXPAND | wx.RIGHT, 5)
		action_buttons_sizer.Add(self.btnEditItem, 1, wx.EXPAND | wx.RIGHT, 5)
		action_buttons_sizer.Add(self.btnDeleteItem, 1, wx.EXPAND | wx.RIGHT, 5)
		action_buttons_sizer.Add(self.btnSettings, 1, wx.EXPAND)
		main_sizer.Add(action_buttons_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

		# Translators: Texto inicial de la barra de estado.
		self.status_text = wx.StaticText(self.panel, label=_("Listo"))
		main_sizer.Add(self.status_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
		self.panel.SetSizerAndFit(main_sizer)

	def bind_events(self):
		self.Bind(wx.EVT_CLOSE, self.on_hide)
		self.search_ctrl.Bind(wx.EVT_TEXT, self.display_items)
		self.search_ctrl.Bind(wx.EVT_KEY_DOWN, self.on_search_key_down)
		self.filter_choice.Bind(wx.EVT_CHOICE, self.on_filter_changed)
		self.category_filter_choice.Bind(wx.EVT_CHOICE, self.display_items)
		self.sort_choice.Bind(wx.EVT_CHOICE, self.display_items)
		self.btnAddItem.Bind(wx.EVT_BUTTON, self.on_add_item)
		self.btnEditItem.Bind(wx.EVT_BUTTON, self.on_edit_item)
		self.btnDeleteItem.Bind(wx.EVT_BUTTON, self.on_delete_item)
		self.btnSettings.Bind(wx.EVT_BUTTON, self.on_settings)
		self.itemList.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_open_item)
		self.itemList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
		self.itemList.Bind(wx.EVT_KEY_DOWN, self.on_item_list_key_down)
		self.itemList.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
		self.Bind(wx.EVT_CHAR_HOOK, self.on_key_press)

	def on_hide(self, event):
		self.Hide()
		gui.mainFrame.postPopup()

	def on_search_key_down(self, event):
		if event.GetKeyCode() == wx.WXK_RETURN:
			if self.itemList.GetItemCount() > 0:
				self.itemList.SetFocus()
				self.itemList.SetItemState(
					0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
					wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED
				)
				self.itemList.EnsureVisible(0)
		else:
			event.Skip()

	def on_key_press(self, event):
		keycode = event.GetKeyCode()
		if keycode == wx.WXK_ESCAPE:
			self.Close()
		else:
			event.Skip()

	def on_filter_changed(self, event):
		is_category_filter = self.filter_choice.GetSelection() == 3
		if is_category_filter:
			self.populate_category_filter()
			self.category_filter_label.Show()
			self.category_filter_choice.Show()
		else:
			self.category_filter_label.Hide()
			self.category_filter_choice.Hide()
		self.panel.GetSizer().Layout()
		self.display_items()

	def populate_category_filter(self):
		self.category_filter_choice.Clear()
		categories = self.db_manager.get_all_categories()
		# Translators: Opción para mostrar todas las categorías.
		self.category_filter_choice.AppendItems([_("Todas")] + categories)
		self.category_filter_choice.SetSelection(0)

	def display_items(self, event=None):
		self.itemList.DeleteAllItems()
		filter_map = {0: 'all', 1: 'url', 2: 'path', 3: 'all'}
		sort_map = {
			0: 'alpha_asc', 1: 'alpha_desc',
			2: 'date_desc', 3: 'date_asc',
			4: 'usage_desc', 5: 'category_asc', 6: 'category_desc'
		}
		filter_by = filter_map.get(self.filter_choice.GetSelection(), 'all')
		sort_by = sort_map.get(self.sort_choice.GetSelection(), 'alpha_asc')
		search_term = self.search_ctrl.GetValue()

		category_filter = None
		if self.filter_choice.GetSelection() == 3 and self.category_filter_choice.GetCount() > 0:
			cat_sel = self.category_filter_choice.GetSelection()
			if cat_sel > 0:
				category_filter = self.category_filter_choice.GetString(cat_sel)

		items = self.db_manager.get_items(
			filter_by=filter_by, sort_by=sort_by,
			category_filter=category_filter, search_term=search_term
		)
		for title, category in items:
			index = self.itemList.InsertItem(self.itemList.GetItemCount(), title)
			self.itemList.SetItem(index, 1, category or UNCATEGORIZED)
		self.restore_focus()

	def on_context_menu(self, event):
		index = self.itemList.GetFirstSelected()
		if index == -1:
			return
		menu = wx.Menu()
		# Translators: Opción del menú contextual para abrir.
		item_open = menu.Append(wx.ID_ANY, _("&Abrir"))
		# Translators: Opción del menú contextual para copiar al portapapeles.
		item_copy = menu.Append(wx.ID_ANY, _("&Copiar al portapapeles\tCtrl+C"))
		menu.AppendSeparator()
		# Translators: Opción del menú contextual para añadir.
		item_add = menu.Append(wx.ID_ANY, _("Añ&adir..."))
		# Translators: Opción del menú contextual para editar.
		item_edit = menu.Append(wx.ID_ANY, _("&Editar...\tCtrl+E"))
		# Translators: Opción del menú contextual para borrar.
		item_delete = menu.Append(wx.ID_ANY, _("&Borrar\tSupr"))
		self.Bind(wx.EVT_MENU, self.on_open_item_from_menu, item_open)
		self.Bind(wx.EVT_MENU, self.on_copy_to_clipboard, item_copy)
		self.Bind(wx.EVT_MENU, self.on_add_item, item_add)
		self.Bind(wx.EVT_MENU, self.on_edit_item, item_edit)
		self.Bind(wx.EVT_MENU, self.on_delete_item, item_delete)
		self.itemList.PopupMenu(menu)
		menu.Destroy()

	def on_open_item_from_menu(self, event):
		index = self.itemList.GetFirstSelected()
		if index == -1:
			return
		title = self.itemList.GetItemText(index)
		self._open_item_by_title(title)

	def on_copy_to_clipboard(self, event):
		index = self.itemList.GetFirstSelected()
		if index == -1:
			return
		title = self.itemList.GetItemText(index)
		item = self.db_manager.get_item_by_title(title)
		if item:
			value = item[1]
			if wx.TheClipboard.Open():
				wx.TheClipboard.SetData(wx.TextDataObject(value))
				wx.TheClipboard.Close()
				# Translators: Mensaje al copiar valor al portapapeles.
				mute(0.3, _("'{0}' copiado al portapapeles.").format(value))

	def on_add_item(self, event):
		# Translators: Título del diálogo para añadir elemento.
		with AddEditDialog(self, _("Añadir Elemento"), self.db_manager) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				title, value, item_type, category = dlg.get_item_data()
				self.db_manager.add_item(title, value, item_type, category)
				self.display_items()
				# Translators: Mensaje al añadir un elemento.
				mute(0.3, _("Elemento '{0}' añadido.").format(title))

	def on_edit_item(self, event):
		index = self.itemList.GetFirstSelected()
		if index == -1:
			return
		title = self.itemList.GetItemText(index)
		# Translators: Título del diálogo para editar elemento.
		with AddEditDialog(self, _("Editar Elemento"), self.db_manager, item_title=title) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				new_title, value, item_type, category = dlg.get_item_data()
				self.db_manager.update_item(title, new_title, value, item_type, category)
				self.display_items()
				# Translators: Mensaje al editar un elemento.
				mute(0.3, _("Elemento '{0}' actualizado.").format(new_title))

	def on_delete_item(self, event):
		index = self.itemList.GetFirstSelected()
		if index == -1:
			return
		title = self.itemList.GetItemText(index)
		if self.db_manager.get_setting("confirm_on_delete", "1") == "1":
			# Translators: Confirmación de borrado de elemento.
			if wx.MessageBox(
				_("¿Borrar el elemento '{0}'?").format(title),
				_("Confirmar"), wx.YES_NO | wx.ICON_QUESTION
			) != wx.YES:
				return
		self.db_manager.delete_item(title)
		self.display_items()
		# Translators: Mensaje al borrar un elemento.
		mute(0.3, _("Elemento '{0}' borrado.").format(title))

	def _open_item_by_title(self, title):
		self.db_manager.increment_usage_count(title)
		item = self.db_manager.get_item_by_title(title)
		if not item:
			return
		_t, value, item_type, _c = item
		try:
			clean_value = value.strip('"')
			if item_type == 'url':
				# Translators: Mensaje al abrir URL.
				mute(0.3, _("Abriendo URL"))
				webbrowser.open(clean_value)
			else:
				# Translators: Mensaje al abrir ruta.
				mute(0.3, _("Abriendo ruta"))
				os.startfile(clean_value)
		except Exception as e:
			# Translators: Error al abrir un elemento.
			wx.MessageBox(
				_("Error al abrir '{0}': {1}").format(value, str(e)),
				_("Error"), wx.OK | wx.ICON_ERROR
			)
		if self.sort_choice.GetSelection() == 4:
			self.display_items()

	def on_open_item(self, event):
		title = event.GetText()
		self._open_item_by_title(title)

	def on_item_selected(self, event):
		title = event.GetText()
		item = self.db_manager.get_item_by_title(title)
		if item:
			value = item[1]
			self.status_text.SetLabel(value)
			self.db_manager.set_setting("last_focused", title)

	def on_settings(self, event):
		# Translators: Título del diálogo de configuración.
		with SettingsDialog(self, _("Configuración"), self.db_manager, self.db_path) as dlg:
			dlg.ShowModal()
		self.display_items()

	def on_item_list_key_down(self, event):
		keycode = event.GetKeyCode()
		if event.ControlDown() and keycode == ord('C'):
			self.on_copy_to_clipboard(event)
		elif event.ControlDown() and keycode == ord('E'):
			self.on_edit_item(event)
		elif keycode == wx.WXK_DELETE:
			self.on_delete_item(event)
		else:
			event.Skip()

	def restore_focus(self):
		last_focused = self.db_manager.get_setting("last_focused")
		if not last_focused:
			return
		for i in range(self.itemList.GetItemCount()):
			if self.itemList.GetItemText(i) == last_focused:
				self.itemList.SetItemState(
					i, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
					wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED
				)
				self.itemList.EnsureVisible(i)
				break

	def add_from_context(self, current_title, current_value):
		# Translators: Título del diálogo al añadir desde contexto.
		with AddEditDialog(self, _("Añadir desde Contexto"), self.db_manager) as dlg:
			dlg.txtTitle.SetValue(current_title)
			dlg.txtValue.SetValue(current_value)
			if dlg.ShowModal() == wx.ID_OK:
				title, value, item_type, category = dlg.get_item_data()
				self.db_manager.add_item(title, value, item_type, category)
				self.display_items()
