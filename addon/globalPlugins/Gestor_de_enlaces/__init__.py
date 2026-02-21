# -*- coding: utf-8 -*-
# Gestor de enlaces
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2024 Ayoub El Bakhti

import os
import webbrowser
import globalVars
import globalPluginHandler
from .from_clipboard import FromClipboard
from .database import DatabaseManager
from .dialogs import LinkManager, validateInput, mute, UNCATEGORIZED
from scriptHandler import script, getLastScriptRepeatCount
import wx
import gui
import ui
import api
import addonHandler

try:
	addonHandler.initTranslation()
except addonHandler.AddonError:
	from logHandler import log
	log.warning('Unable to initialise translations. This may be because the addon is running from NVDA scratchpad.')


def _get_db_path():
	return os.path.join(globalVars.appArgs.configPath, "gestor_enlaces.db")


def _get_json_path():
	return os.path.join(globalVars.appArgs.configPath, "links.json")


def disableInSecureMode(decoratedCls):
	if globalVars.appArgs.secure:
		return globalPluginHandler.GlobalPlugin
	return decoratedCls


@disableInSecureMode
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super(GlobalPlugin, self).__init__()
		self.link_manager = None
		self.addLinkInfo = "", ""

		self._nav_links = []
		self._nav_categories = []
		self._nav_link_index = -1
		self._nav_cat_index = -1

		self._db_path = _get_db_path()
		try:
			self._db_manager = DatabaseManager(self._db_path)
		except Exception as e:
			from logHandler import log
			log.error("Gestor de Enlaces: Error al inicializar la base de datos: %s" % str(e))
			self._db_manager = None
			return

		self._auto_migrate()

	def _auto_migrate(self):
		json_path = _get_json_path()
		if os.path.exists(json_path) and self._db_manager.get_item_count() == 0:
			try:
				rows = self._db_manager.migrate_from_json(json_path)
				if rows > 0:
					from logHandler import log
					log.info(f"Gestor de Enlaces: {rows} elementos migrados desde links.json a SQLite.")
			except Exception as e:
				from logHandler import log
				log.error(f"Gestor de Enlaces: Error en migración automática: {e}")

	def terminate(self):
		if self._db_manager:
			self._db_manager.close()
		if self.link_manager:
			self.link_manager.Destroy()
			self.link_manager = None
		super(GlobalPlugin, self).terminate()

	def create_or_toggle_link_manager(self, addLink=False):
		if not self._db_manager:
			# Translators: Error cuando la base de datos no pudo inicializarse.
			ui.message(_("Error: la base de datos no se pudo inicializar."))
			return

		try:
			if not self.link_manager:
				# Translators: Título del diálogo principal.
				self.link_manager = LinkManager(gui.mainFrame, _('Gestor de Enlaces'), self._db_manager, self._db_path)

			if self.link_manager.IsShown():
				try:
					is_active = self.link_manager.IsActive()
				except AttributeError:
					is_active = True
				if not is_active:
					self.link_manager.Hide()

			if not self.link_manager.IsShown():
				gui.mainFrame.prePopup()
				self.link_manager.Show()

			title, url = self.addLinkInfo
			if addLink and url:
				is_valid, _item_type = validateInput(url)
				if is_valid:
					self.link_manager.add_from_context(
						# Translators: Título por defecto cuando no se detecta título.
						title if title else _("Sin título"), url
					)
					self.addLinkInfo = "", ""
		except Exception as e:
			from logHandler import log
			log.error("Gestor de Enlaces: Error al abrir el gestor: %s" % str(e))
			# Translators: Mensaje de error al abrir el gestor.
			ui.message(_("Error al abrir el gestor de enlaces."))

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

	# Translators: Descripción del script para abrir el gestor de enlaces.
	@script(
		description=_("Abre la ventana del gestor de enlaces"),
		gesture="kb:NVDA+alt+k",
		category=_("Gestor De Enlaces")
	)
	def script_open_file(self, gesture):
		addLink = False
		if getLastScriptRepeatCount() == 0:
			self.refreshLinkInfo()
		elif getLastScriptRepeatCount() == 1:
			addLink = True
		wx.CallAfter(self.create_or_toggle_link_manager, addLink)

	@script(
		# Translators: Descripción del script para abrir enlace desde portapapeles.
		description=_("Abrir enlace desde el portapapeles"),
		gesture="kb:NVDA+z",
		category=_("Gestor De Enlaces")
	)
	def script_open_clipboard_link(self, gesture):
		wx.CallAfter(FromClipboard, gui.mainFrame)

	def _refresh_nav_data(self):
		all_items = self._db_manager.get_all_items_for_nav()
		self._nav_links = []
		for title, value, item_type, cat_name in all_items:
			self._nav_links.append((title, value, cat_name or UNCATEGORIZED))

		all_cats = set()
		for _title, _value, cat in self._nav_links:
			all_cats.add(cat)
		for c in self._db_manager.get_all_categories():
			all_cats.add(c)
		self._nav_categories = sorted(list(all_cats), key=lambda s: s.lower())

	def _get_filtered_links(self):
		if self._nav_cat_index < 0 or self._nav_cat_index >= len(self._nav_categories):
			return self._nav_links
		selected_cat = self._nav_categories[self._nav_cat_index]
		return [(t, u, c) for t, u, c in self._nav_links if selected_cat == c]

	@script(
		# Translators: Descripción del script para ir al enlace siguiente.
		description=_("Ir al enlace siguiente"),
		gesture=None,
		category=_("Gestor De Enlaces")
	)
	def script_next_link(self, gesture):
		self._refresh_nav_data()
		filtered = self._get_filtered_links()
		if not filtered:
			# Translators: Mensaje cuando no hay enlaces disponibles.
			ui.message(_("No hay enlaces"))
			return
		self._nav_link_index += 1
		if self._nav_link_index >= len(filtered):
			self._nav_link_index = len(filtered) - 1
		title, value, _cat = filtered[self._nav_link_index]
		# Translators: Se anuncia el enlace con su posición.
		ui.message(_("{title}: {value}, {pos} de {total}").format(
			title=title, value=value, pos=self._nav_link_index + 1, total=len(filtered)
		))

	@script(
		# Translators: Descripción del script para ir al enlace anterior.
		description=_("Ir al enlace anterior"),
		gesture=None,
		category=_("Gestor De Enlaces")
	)
	def script_previous_link(self, gesture):
		self._refresh_nav_data()
		filtered = self._get_filtered_links()
		if not filtered:
			# Translators: Mensaje cuando no hay enlaces disponibles.
			ui.message(_("No hay enlaces"))
			return
		self._nav_link_index -= 1
		if self._nav_link_index < 0:
			self._nav_link_index = 0
		title, value, _cat = filtered[self._nav_link_index]
		# Translators: Se anuncia el enlace con su posición.
		ui.message(_("{title}: {value}, {pos} de {total}").format(
			title=title, value=value, pos=self._nav_link_index + 1, total=len(filtered)
		))

	@script(
		# Translators: Descripción del script para abrir el enlace actual.
		description=_("Abrir enlace actual en el navegador"),
		gesture=None,
		category=_("Gestor De Enlaces")
	)
	def script_open_current_link(self, gesture):
		self._refresh_nav_data()
		filtered = self._get_filtered_links()
		if not filtered or self._nav_link_index < 0 or self._nav_link_index >= len(filtered):
			# Translators: Mensaje cuando no hay enlace seleccionado.
			ui.message(_("No hay ningún enlace seleccionado"))
			return
		title, value, _cat = filtered[self._nav_link_index]
		# Translators: Mensaje al abrir URL.
		ui.message(_("Abriendo {url}").format(url=value))
		webbrowser.open(value)

	@script(
		# Translators: Descripción del script para ir a la categoría siguiente.
		description=_("Ir a la categoría siguiente"),
		gesture=None,
		category=_("Gestor De Enlaces")
	)
	def script_next_category(self, gesture):
		self._refresh_nav_data()
		if not self._nav_categories:
			# Translators: Mensaje cuando no hay categorías disponibles.
			ui.message(_("No hay categorías"))
			return
		self._nav_cat_index += 1
		if self._nav_cat_index >= len(self._nav_categories):
			self._nav_cat_index = len(self._nav_categories) - 1
		cat_name = self._nav_categories[self._nav_cat_index]
		count = sum(1 for _t, _u, c in self._nav_links if cat_name == c)
		# Translators: Se anuncia la categoría con su posición y cantidad de enlaces.
		ui.message(_("{name}, {count} enlaces, {pos} de {total}").format(
			name=cat_name, count=count, pos=self._nav_cat_index + 1, total=len(self._nav_categories)
		))
		self._nav_link_index = -1

	@script(
		# Translators: Descripción del script para ir a la categoría anterior.
		description=_("Ir a la categoría anterior"),
		gesture=None,
		category=_("Gestor De Enlaces")
	)
	def script_previous_category(self, gesture):
		self._refresh_nav_data()
		if not self._nav_categories:
			# Translators: Mensaje cuando no hay categorías disponibles.
			ui.message(_("No hay categorías"))
			return
		self._nav_cat_index -= 1
		if self._nav_cat_index < 0:
			self._nav_cat_index = 0
		cat_name = self._nav_categories[self._nav_cat_index]
		count = sum(1 for _t, _u, c in self._nav_links if cat_name == c)
		# Translators: Se anuncia la categoría con su posición y cantidad de enlaces.
		ui.message(_("{name}, {count} enlaces, {pos} de {total}").format(
			name=cat_name, count=count, pos=self._nav_cat_index + 1, total=len(self._nav_categories)
		))
		self._nav_link_index = -1
