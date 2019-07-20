import pcbnew
import os
import shutil
import wx
import locale
import zipfile

outputDirName = "gerber_to_order"

layers = [
    [ pcbnew.F_Cu,      'F_Cu' ],
    [ pcbnew.B_Cu,      'B_Cu' ],
    [ pcbnew.F_SilkS,   'F_Silks' ],
    [ pcbnew.B_SilkS,   'B_Silks' ],
    [ pcbnew.F_Mask,    'F_Mask' ],
    [ pcbnew.B_Mask,    'B_Mask' ],
    [ pcbnew.Edge_Cuts, 'Edge_Cuts' ],
    [ pcbnew.In1_Cu,    'In1_Cu' ],
    [ pcbnew.In2_Cu,    'In2_Cu' ],
    [ pcbnew.In3_Cu,    'In3_Cu' ],
    [ pcbnew.In4_Cu,    'In4_Cu' ],
]

pcbServices = [
    {
        "name": "Elecrow",
        "mergeNpth": False,
        "useAuxOrigin": True,
        "excellonFormat": pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT, # pcbnew.EXCELLON_WRITER.SUPPRESS_LEADING
        "layerRenameRules": [
            [ pcbnew.F_Cu,     '[boardProjectName].GTL' ],
            [ pcbnew.B_Cu,     '[boardProjectName].GBL' ],
            [ pcbnew.F_SilkS,  '[boardProjectName].GTO' ],
            [ pcbnew.B_SilkS,  '[boardProjectName].GBO' ],
            [ pcbnew.F_Mask,   '[boardProjectName].GTS' ],
            [ pcbnew.B_Mask,   '[boardProjectName].GBS' ],
            [ pcbnew.Edge_Cuts,'[boardProjectName].GML' ],
            [ pcbnew.In1_Cu,   '[boardProjectName].G1' ],
            [ pcbnew.In2_Cu,   '[boardProjectName].G2' ],
            [ pcbnew.In3_Cu,   '[boardProjectName].G3' ],
            [ pcbnew.In4_Cu,   '[boardProjectName].G4' ],
        ],
        "drillExtensionRenameTo": 'TXT',
    }
]

def removeFile(fileName):
    if os.path.exists(fileName):
        os.remove(fileName)

def renameFile(src, dst):
    removeFile(dst)
    os.rename(src, dst)

def createZip(pcbServiceName, mergeNpth, useAuxOrigin, excellonFormat,
              gerberProtelExtensions = False,
              layerRenameRules = [],
              drillExtensionRenameTo = None):
    board = pcbnew.GetBoard()
    boardFileName = board.GetFileName()
    boardDirPath = os.path.dirname(boardFileName)
    boardProjectName = (os.path.splitext(os.path.basename(boardFileName)))[0]

    outputDirPath = '%s/%s' % (boardDirPath, outputDirName)
    gerberDirName = '%s_for_%s' % (boardProjectName, pcbServiceName)
    gerberDirPath = '%s/%s' % (outputDirPath, gerberDirName)
    zipFilePath = '%s/%s.zip' % (outputDirPath, gerberDirName)

    if not os.path.exists(outputDirPath):
        os.mkdir(outputDirPath)
    if os.path.exists(gerberDirPath):
        shutil.rmtree(gerberDirPath)
    os.mkdir(gerberDirPath)
    targetLayerCount = board.GetCopperLayerCount() + 5

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
    po.SetUseGerberProtelExtensions(gerberProtelExtensions)

    for i in range(targetLayerCount):
        layer = layers[i]
        layerTypeName = layer[1]
        pc.SetLayer(layer[0])
        pc.OpenPlotfile(layerTypeName, pcbnew.PLOT_FORMAT_GERBER, layerTypeName)
        pc.PlotLayer()
        plotFilePath = pc.GetPlotFileName()

        if len(layerRenameRules) > 0:
            layer = layers[i]
            newFileName = layerRenameRules[i][1] # TODO select by layer type
            newFileName = newFileName.replace('[boardProjectName]', boardProjectName)
            newFilePath = '%s/%s' % (gerberDirPath, newFileName)
            renameFile(plotFilePath, newFilePath)
    pc.ClosePlot()

    # DRILL
    ew = pcbnew.EXCELLON_WRITER(board)
    ew.SetFormat(True, excellonFormat, 3, 3)
    offset = pcbnew.wxPoint(0,0)
    if(useAuxOrigin):
        offset = board.GetAuxOrigin()
    ew.SetOptions(False, False, offset, mergeNpth)
    ew.CreateDrillandMapFilesSet(gerberDirPath,True,False)
    if drillExtensionRenameTo is not None:
        if mergeNpth:
            renameFile('%s/%s.drl' % (gerberDirPath, boardProjectName),
                       '%s/%s.%s' % (gerberDirPath, boardProjectName, drillExtensionRenameTo))
        else:
            renameFile('%s/%s-PTH.drl' % (gerberDirPath, boardProjectName),
                       '%s/%s-PTH.%s' % (gerberDirPath, boardProjectName, drillExtensionRenameTo))
            renameFile('%s/%s-NPTH.drl' % (gerberDirPath, boardProjectName),
                       '%s/%s-NPTH.%s' % (gerberDirPath, boardProjectName, drillExtensionRenameTo))

    # ZIP
    removeFile(zipFilePath)
    shutil.make_archive(zipFilePath, 'zip', outputDirPath, gerberDirName)

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
                    zipFiles = []
                    for pcbService in pcbServices:
                        path = createZip(
                            pcbServiceName = pcbService['name'],
                            mergeNpth = pcbService['mergeNpth'],
                            useAuxOrigin = pcbService['useAuxOrigin'],
                            excellonFormat = pcbService['excellonFormat'],
                            layerRenameRules = pcbService['layerRenameRules'],
                            drillExtensionRenameTo = pcbService['drillExtensionRenameTo'],
                        )
                        zipFiles.append(path)
                    # wx.MessageBox(getstr('COMPLETE')%zip_fname, 'Gerber Zip', wx.OK|wx.ICON_INFORMATION)
                    wx.MessageBox('Exported ' + str(zipFiles), 'Gerber to order', wx.OK|wx.ICON_INFORMATION)
                except Exception as e:
                    wx.MessageBox('Error: ' + str(e), 'Gerber to order', wx.OK|wx.ICON_INFORMATION)
                e.Skip()
        dialog = Dialog(None)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
