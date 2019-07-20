import pcbnew
import os
import wx
import locale
import zipfile

outputDirName = "gerber_to_order"

layers = [
    [ pcbnew.F_Cu,     'GTL', None ],
    [ pcbnew.B_Cu,     'GBL', None ],
    [ pcbnew.F_SilkS,  'GTO', None ],
    [ pcbnew.B_SilkS,  'GBO', None ],
    [ pcbnew.F_Mask,   'GTS', None ],
    [ pcbnew.B_Mask,   'GBS', None ],
    [ pcbnew.Edge_Cuts,'GML', None ],
    [ pcbnew.In1_Cu,   'GL2', None ],
    [ pcbnew.In2_Cu,   'GL3', None ],
    [ pcbnew.In3_Cu,   'GL4', None ],
    [ pcbnew.In4_Cu,   'GL5', None ],
]

def removeFile(fileName):
    if os.path.exists(fileName):
        os.remove(fileName)

def renameFile(src, dst):
    removeFile(dst)
    os.rename(src, dst)

def createZip(pcbServiceName, mergeNpth, useAuxOrigin, excellonFormat):
    board = pcbnew.GetBoard()
    boardFileName = board.GetFileName()
    boardDirPath = os.path.dirname(boardFileName)
    boardProjectName = (os.path.splitext(os.path.basename(boardFileName)))[0]

    outputDirPath = '%s/%s' % (boardDirPath, outputDirName)
    gerberDirPath = '%s/%s' % (outputDirPath, pcbServiceName)
    drillFilePath = '%s/%s.TXT' % (gerberDirPath, boardProjectName)
    npthFilePath = '%s/%s-NPTH.TXT' % (gerberDirPath, boardProjectName)
    zipFilePath = '%s/%s_for_%s.zip' % (outputDirPath, boardProjectName, pcbServiceName)
    if not os.path.exists(outputDirPath):
        os.mkdir(outputDirPath)
    if not os.path.exists(gerberDirPath):
        os.mkdir(gerberDirPath)
    maxLayer = board.GetCopperLayerCount() + 5

    # PLOT
    pc = pcbnew.PLOT_CONTROLLER(board)
    po = pc.GetPlotOptions()

    po.SetOutputDirectory(gerberDirPath)
    po.SetPlotValue(True)
    po.SetPlotReference(True)
    po.SetExcludeEdgeLayer(False)
    po.SetLineWidth(pcbnew.FromMM(0.1))
    po.SetSubtractMaskFromSilk(True)
    po.SetUseAuxOrigin(useAuxOrigin)

    for layer in layers:
        targetname = '%s/%s.%s' % (gerberDirPath, boardProjectName, layer[1])
        removeFile(targetname)
    removeFile(drillFilePath)
    removeFile(npthFilePath)
    removeFile(zipFilePath)

    for i in range(maxLayer):
        layer = layers[i]
        pc.SetLayer(layer[0])
        pc.OpenPlotfile(layer[1], pcbnew.PLOT_FORMAT_GERBER, layer[1])
        pc.PlotLayer()
        layer[2] = pc.GetPlotFileName()
    pc.ClosePlot()

    for i in range(maxLayer):
        layer = layers[i]
        targetName = '%s/%s.%s' % (gerberDirPath, boardProjectName, layer[1])
        renameFile(layer[2],targetName)

    # DRILL
    ew = pcbnew.EXCELLON_WRITER(board)
    ew.SetFormat(True, excellonFormat, 3, 3)
    offset = pcbnew.wxPoint(0,0)
    if(useAuxOrigin):
        offset = board.GetAuxOrigin()
    ew.SetOptions(False, False, offset, mergeNpth)
    ew.CreateDrillandMapFilesSet(gerberDirPath,True,False)
    if mergeNpth:
        renameFile('%s/%s.drl' % (gerberDirPath, boardProjectName), drillFilePath)
    else:
        renameFile('%s/%s-PTH.drl' % (gerberDirPath, boardProjectName), drillFilePath)
        renameFile('%s/%s-NPTH.drl' % (gerberDirPath, boardProjectName), npthFilePath)

    # ZIP
    with zipfile.ZipFile(zipFilePath,'w') as f:
        for i in range(maxLayer):
            layer = layers[i]
            targetname = '%s/%s.%s' % (gerberDirPath, boardProjectName, layer[1])
            f.write(targetname, os.path.basename(targetname))
        f.write(drillFilePath, os.path.basename(drillFilePath))
        if not mergeNpth:
            f.write(npthFilePath, os.path.basename(npthFilePath))

    return zipFilePath

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
                # self.mergeNpth.SetValue(mergeNpth)
                # self.useAuxOrigin.SetValue(useAuxOrigin)
                self.clsbtn.Bind(wx.EVT_BUTTON, self.OnClose)
                self.execbtn.Bind(wx.EVT_BUTTON, self.OnExec)
            def OnClose(self,e):
                e.Skip()
                self.Close()
            def OnExec(self,e):
                # mergeNpth = True if self.mergeNpth.GetValue() else False
                # useAuxOrigin = True if self.useAuxOrigin.GetValue() else False
                # excellonFormat = (EXCELLON_WRITER.DECIMAL_FORMAT, EXCELLON_WRITER.SUPPRESS_LEADING)[self.zeros.GetSelection()]
                try:
                    zipFilePath = createZip(
                        pcbServiceName = 'Elecrow',
                        mergeNpth = False,
                        useAuxOrigin = True,
                        excellonFormat = pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT # pcbnew.EXCELLON_WRITER.SUPPRESS_LEADING
                    )
                    # wx.MessageBox(getstr('COMPLETE')%zip_fname, 'Gerber Zip', wx.OK|wx.ICON_INFORMATION)
                    wx.MessageBox(zipFilePath, 'Gerber to order', wx.OK|wx.ICON_INFORMATION)
                except Exception as e:
                    wx.MessageBox('Error: ' + str(e), 'Gerber to order', wx.OK|wx.ICON_INFORMATION)
                e.Skip()
        dialog = Dialog(None)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
