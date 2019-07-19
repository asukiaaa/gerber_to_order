import pcbnew
import os
import wx
import locale
import zipfile

merge_npth = False
use_aux_origin = True

class GerberToOrderAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Gerber to order"
        self.category = "A descriptive category name"
        self.description = "A plugin to creage zip compressed gerber files to order PCB for Elecrow, FusionPCB or PCBWay."
        self.show_toolbar_button = False # Optional, defaults to False
        # self.icon_file_name = os.path.join(os.path.dirname(__file__), 'simple_plugin.png') # Optional, defaults to ""

    def Run(self):
        class Dialog(wx.Dialog):
            def __init__(self, parent):
                wx.Dialog.__init__(self, parent, id=-1, title='Gerber to order')
                self.panel = wx.Panel(self)
                self.description = wx.StaticText(self.panel, wx.ID_ANY, "hello world", pos=(20,10))
                # self.mergeNpth = wx.CheckBox(self.panel, wx.ID_ANY, getstr('MERGE',lang), pos=(30,40))
                # self.useAuxOrigin = wx.CheckBox(self.panel, wx.ID_ANY, getstr('AUXORIG',lang), pos=(30,60))
                # self.zeros = wx.RadioBox(self.panel,wx.ID_ANY, getstr('ZEROS',lang), pos=(30,90), choices=[getstr('DECIMAL',lang), getstr('SUPPRESS',lang)], style=wx.RA_HORIZONTAL)
                self.execbtn = wx.Button(self.panel, wx.ID_ANY, 'exec', pos=(30,150))
                self.clsbtn = wx.Button(self.panel, wx.ID_ANY, 'close', pos=(170,150))
                # self.mergeNpth.SetValue(merge_npth)
                # self.useAuxOrigin.SetValue(use_aux_origin)
                self.clsbtn.Bind(wx.EVT_BUTTON, self.OnClose)
                self.execbtn.Bind(wx.EVT_BUTTON, self.OnExec)
            def OnClose(self,e):
                e.Skip()
                self.Close()
            def OnExec(self,e):
                # merge_npth = True if self.mergeNpth.GetValue() else False
                # use_aux_origin = True if self.useAuxOrigin.GetValue() else False
                # excellon_format = (EXCELLON_WRITER.DECIMAL_FORMAT, EXCELLON_WRITER.SUPPRESS_LEADING)[self.zeros.GetSelection()]
                # Exec()
                # wx.MessageBox(getstr('COMPLETE')%zip_fname, 'Gerber Zip', wx.OK|wx.ICON_INFORMATION)
                e.Skip()
        dialog = Dialog(None)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
