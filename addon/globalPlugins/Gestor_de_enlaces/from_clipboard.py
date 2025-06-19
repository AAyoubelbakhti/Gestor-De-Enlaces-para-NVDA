# Código basado en https://github.com/abdallah-hader/linkManager
# Créditos a: Abdallah Hayder

import addonHandler
addonHandler.initTranslation()
import api
import wx
import webbrowser as wb
import re
from ui import message, reportTextCopiedToClipboard

# Expresión regular para extraer URLs
url_re = re.compile(r"(?:\w+://|www\.)[^ ,.\?!#%=+\[\]{}\"\'()\\]+[^ \r]*")
bad_chars = '\'\\.,[](){}:;"'

def extract_urls(text):
	"""Extrae y limpia URLs desde texto plano"""
	return [s.strip(bad_chars) for s in url_re.findall(text)]

class FromClipboard(wx.Dialog):
	def __init__(self, parent):
		try:
			clip = api.getClipData()
			links = extract_urls(clip)
			if len(links) < 1:
				raise OSError("no links found")
		except OSError:
			return message(_("El portapepeles Está vacío, no hay enlace o el mismo no es válido"))
		
		if len(links) == 1:
			message(_("opening {url}").format(url=links[0]))
			return wb.open(links[0])

		super().__init__(parent, -1, _("Choose a link to open"))
		p = wx.Panel(self)
		wx.StaticText(p, -1, _("{count} links found").format(count=len(links)))
		self.linksList = wx.ListBox(p, -1)
		openUrl = wx.Button(p, -1, _("open"))
		openUrl.SetDefault()
		openUrl.Bind(wx.EVT_BUTTON, self.OnOpen)
		copy = wx.Button(p, -1, _("copy to clipboard"))
		copy.Bind(wx.EVT_BUTTON, self.OnCopy)
		close = wx.Button(p, wx.ID_CANCEL, _("close"))

		for link in links:
			self.linksList.Append(link)

		self.linksList.Selection = 0
		wx.CallAfter(self.Show)

	def OnOpen(self, event):
		message(_("opening {url}").format(url=self.linksList.StringSelection))
		wb.open(self.linksList.StringSelection)

	def OnCopy(self, event):
		if api.copyToClip(self.linksList.StringSelection):
			reportTextCopiedToClipboard(self.linksList.StringSelection)