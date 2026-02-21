# -*- coding: utf-8 -*-
# Gestor de enlaces - Módulo de base de datos SQLite
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2024 Ayoub El Bakhti

import os
import sys
import json

dirAddon = os.path.dirname(__file__)
sys.path.append(dirAddon)
sys.path.append(os.path.join(dirAddon, "lib"))
if sys.version.startswith("3.11"):
	sys.path.append(os.path.join(dirAddon, "lib", "_311"))
	from .lib._311 import sqlite3
	sqlite3.__path__.append(os.path.join(dirAddon, "lib", "_311", "sqlite3"))
elif sys.version.startswith("3.13"):
	sys.path.append(os.path.join(dirAddon, "lib", "_313"))
	from .lib._313 import sqlite3
	sqlite3.__path__.append(os.path.join(dirAddon, "lib", "_313", "sqlite3"))
else:
	sys.path.append(os.path.join(dirAddon, "lib", "_37"))
	from .lib._37 import sqlite3
	sqlite3.__path__.append(os.path.join(dirAddon, "lib", "_37", "sqlite3"))
del sys.path[-3:]


UNCATEGORIZED = "Sin categoría"


class DatabaseManager:
	def __init__(self, db_path):
		self.db_path = db_path
		self.conn = sqlite3.connect(db_path, check_same_thread=False)
		self.conn.execute("PRAGMA foreign_keys = ON")
		self.create_tables()
		self._add_usage_count_column()
		self.add_category(UNCATEGORIZED)

	def _add_usage_count_column(self):
		cursor = self.conn.cursor()
		try:
			cursor.execute("SELECT usage_count FROM items LIMIT 1")
		except sqlite3.OperationalError:
			cursor.execute("ALTER TABLE items ADD COLUMN usage_count INTEGER NOT NULL DEFAULT 0")
			self.conn.commit()

	def create_tables(self):
		cursor = self.conn.cursor()
		cursor.execute('''
			CREATE TABLE IF NOT EXISTS categories (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL UNIQUE
			)
		''')
		cursor.execute('''
			CREATE TABLE IF NOT EXISTS items (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				title TEXT NOT NULL UNIQUE,
				value TEXT NOT NULL,
				type TEXT NOT NULL,
				category_id INTEGER,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL
			)
		''')
		cursor.execute('''
			CREATE TABLE IF NOT EXISTS settings (
				key TEXT PRIMARY KEY,
				value TEXT
			)
		''')
		self.conn.commit()

	def get_category_id(self, name, create_if_not_exists=False):
		cursor = self.conn.cursor()
		cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
		result = cursor.fetchone()
		if result:
			return result[0]
		if create_if_not_exists:
			cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
			self.conn.commit()
			return cursor.lastrowid
		return None

	def get_all_categories(self):
		cursor = self.conn.cursor()
		cursor.execute("SELECT name FROM categories ORDER BY name COLLATE NOCASE ASC")
		return [row[0] for row in cursor.fetchall()]

	def add_category(self, name):
		cursor = self.conn.cursor()
		cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
		self.conn.commit()

	def rename_category(self, old_name, new_name):
		cursor = self.conn.cursor()
		cursor.execute("UPDATE categories SET name = ? WHERE name = ?", (new_name, old_name))
		self.conn.commit()

	def delete_category(self, name, default_category=None):
		if default_category is None:
			default_category = UNCATEGORIZED
		default_cat_id = self.get_category_id(default_category, create_if_not_exists=True)
		cat_to_delete_id = self.get_category_id(name)
		if not cat_to_delete_id:
			return
		cursor = self.conn.cursor()
		cursor.execute("UPDATE items SET category_id = ? WHERE category_id = ?", (default_cat_id, cat_to_delete_id))
		cursor.execute("DELETE FROM categories WHERE id = ?", (cat_to_delete_id,))
		self.conn.commit()

	def add_item(self, title, value, item_type, category_name):
		cat_id = self.get_category_id(category_name, create_if_not_exists=True)
		cursor = self.conn.cursor()
		cursor.execute(
			"INSERT INTO items (title, value, type, category_id) VALUES (?, ?, ?, ?)",
			(title, value, item_type, cat_id)
		)
		self.conn.commit()

	def update_item(self, old_title, new_title, value, item_type, category_name):
		cat_id = self.get_category_id(category_name, create_if_not_exists=True)
		cursor = self.conn.cursor()
		cursor.execute(
			"UPDATE items SET title=?, value=?, type=?, category_id=? WHERE title=?",
			(new_title, value, item_type, cat_id, old_title)
		)
		self.conn.commit()

	def delete_item(self, title):
		cursor = self.conn.cursor()
		cursor.execute("DELETE FROM items WHERE title=?", (title,))
		self.conn.commit()

	def get_item_by_title(self, title):
		cursor = self.conn.cursor()
		cursor.execute(
			"SELECT i.title, i.value, i.type, c.name "
			"FROM items i LEFT JOIN categories c ON i.category_id = c.id "
			"WHERE i.title = ?",
			(title,)
		)
		return cursor.fetchone()

	def get_items(self, filter_by='all', sort_by='alpha_asc', category_filter=None, search_term=None):
		query = "SELECT i.title, c.name FROM items i LEFT JOIN categories c ON i.category_id = c.id"
		where_clauses = []
		params = []

		if filter_by != 'all':
			where_clauses.append("i.type = ?")
			params.append(filter_by)

		if category_filter:
			where_clauses.append("c.name = ?")
			params.append(category_filter)

		if search_term:
			where_clauses.append("i.title LIKE ?")
			params.append(f"%{search_term}%")

		if where_clauses:
			query += " WHERE " + " AND ".join(where_clauses)

		sort_map = {
			'alpha_asc': " ORDER BY i.title COLLATE NOCASE ASC",
			'alpha_desc': " ORDER BY i.title COLLATE NOCASE DESC",
			'date_desc': " ORDER BY i.created_at DESC",
			'date_asc': " ORDER BY i.created_at ASC",
			'usage_desc': " ORDER BY i.usage_count DESC, i.title COLLATE NOCASE ASC",
			'category_asc': " ORDER BY c.name COLLATE NOCASE ASC, i.title COLLATE NOCASE ASC",
			'category_desc': " ORDER BY c.name COLLATE NOCASE DESC, i.title COLLATE NOCASE ASC",
		}
		query += sort_map.get(sort_by, " ORDER BY i.title COLLATE NOCASE ASC")

		cursor = self.conn.cursor()
		cursor.execute(query, tuple(params))
		return cursor.fetchall()

	def increment_usage_count(self, title):
		cursor = self.conn.cursor()
		cursor.execute("UPDATE items SET usage_count = usage_count + 1 WHERE title = ?", (title,))
		self.conn.commit()

	def get_all_items_for_nav(self):
		cursor = self.conn.cursor()
		cursor.execute(
			"SELECT i.title, i.value, i.type, c.name "
			"FROM items i LEFT JOIN categories c ON i.category_id = c.id "
			"ORDER BY i.title COLLATE NOCASE ASC"
		)
		return cursor.fetchall()

	def get_setting(self, key, default=None):
		cursor = self.conn.cursor()
		cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
		row = cursor.fetchone()
		return row[0] if row else default

	def set_setting(self, key, value):
		cursor = self.conn.cursor()
		cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
		self.conn.commit()

	def read_data_from_backup(self, backup_path):
		backup_conn = sqlite3.connect(backup_path)
		backup_cursor = backup_conn.cursor()

		backup_cursor.execute("SELECT name FROM categories")
		categories = [row[0] for row in backup_cursor.fetchall()]

		backup_cursor.execute(
			"SELECT title, value, type, c.name "
			"FROM items i LEFT JOIN categories c ON i.category_id = c.id"
		)
		items = []
		for row in backup_cursor.fetchall():
			items.append({
				"title": row[0], "value": row[1], "type": row[2],
				"category": row[3] or UNCATEGORIZED
			})

		backup_cursor.execute("SELECT key, value FROM settings")
		settings = backup_cursor.fetchall()

		backup_conn.close()
		return {"categories": categories, "items": items, "settings": settings}

	def merge_data_from_backup(self, data):
		cursor = self.conn.cursor()

		for cat_name in data.get("categories", []):
			self.add_category(cat_name)

		items_to_insert = []
		for item in data.get("items", []):
			cat_id = self.get_category_id(item["category"], create_if_not_exists=True)
			items_to_insert.append((item["title"], item["value"], item["type"], cat_id))

		if items_to_insert:
			cursor.executemany(
				"INSERT OR IGNORE INTO items (title, value, type, category_id) VALUES (?, ?, ?, ?)",
				items_to_insert
			)

		settings_to_insert = data.get("settings", [])
		if settings_to_insert:
			cursor.executemany(
				"INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
				settings_to_insert
			)

		self.conn.commit()

	def migrate_from_json(self, json_path):
		if not os.path.exists(json_path):
			return 0

		try:
			with open(json_path, 'r', encoding='utf-8') as f:
				data = json.load(f)
		except (json.JSONDecodeError, IOError):
			return 0

		user_cats = data.get("__user_defined_categories__", [])
		if isinstance(user_cats, list):
			for cat_name in user_cats:
				self.add_category(cat_name)

		rows_added = 0
		for title, item_data in data.items():
			if title == "__user_defined_categories__":
				continue

			value = ""
			item_type = "url"
			category = UNCATEGORIZED

			if isinstance(item_data, str):
				value = item_data
			elif isinstance(item_data, dict):
				value = item_data.get("url", item_data.get("path", ""))
				if "path" in item_data and "url" not in item_data:
					item_type = "path"
				cats = item_data.get("categories", [])
				if isinstance(cats, list) and cats:
					category = cats[0]
				elif isinstance(cats, str) and cats:
					category = cats
			else:
				continue

			if not value:
				continue

			try:
				self.add_item(title, value, item_type, category)
				rows_added += 1
			except sqlite3.IntegrityError:
				continue

		return rows_added

	def get_item_count(self):
		cursor = self.conn.cursor()
		cursor.execute("SELECT COUNT(*) FROM items")
		return cursor.fetchone()[0]

	def clear_all_data(self):
		cursor = self.conn.cursor()
		cursor.execute("DELETE FROM items")
		cursor.execute("DELETE FROM categories")
		cursor.execute("DELETE FROM settings")
		self.conn.commit()
		self.add_category(UNCATEGORIZED)

	def close(self):
		if self.conn:
			self.conn.close()
			self.conn = None

	def reconnect(self):
		if not self.conn:
			self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
			self.conn.execute("PRAGMA foreign_keys = ON")
