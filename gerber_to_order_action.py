import pcbnew
import os
import shutil
import wx
import locale
import zipfile
import datetime

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
        "useAuxOrigin": True,
        "gerberProtelExtensions": False,
        "excellonFormat": pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT,
        "drillMergeNpth": False,
        "drillMinimalHeader": False,
        "layerRenameRules": {
            pcbnew.F_Cu:      '[boardProjectName].GTL',
            pcbnew.B_Cu:      '[boardProjectName].GBL',
            pcbnew.F_SilkS:   '[boardProjectName].GTO',
            pcbnew.B_SilkS:   '[boardProjectName].GBO',
            pcbnew.F_Mask:    '[boardProjectName].GTS',
            pcbnew.B_Mask:    '[boardProjectName].GBS',
            pcbnew.Edge_Cuts: '[boardProjectName].GML',
            pcbnew.In1_Cu:    '[boardProjectName].G1',
            pcbnew.In2_Cu:    '[boardProjectName].G2',
            pcbnew.In3_Cu:    '[boardProjectName].G3',
            pcbnew.In4_Cu:    '[boardProjectName].G4',
        },
        "drillExtensionRenameTo": 'TXT',
    },
    {
        "name": "FusionPCB",
        "useAuxOrigin": True,
        "gerberProtelExtensions": True,
        "excellonFormat": pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT,
        "drillMergeNpth": True,
        "drillMinimalHeader": False,
        "layerRenameRules": {},
        "drillExtensionRenameTo": None,
    },
    {
        "name": "PCBWay",
        "useAuxOrigin": True,
        "gerberProtelExtensions": False,
        "excellonFormat": pcbnew.EXCELLON_WRITER.SUPPRESS_LEADING,
        "drillMergeNpth": False,
        "drillMinimalHeader": True,
        "layerRenameRules": {},
        "drillExtensionRenameTo": None,
    },
]

def removeFile(fileName):
    if os.path.exists(fileName):
        os.remove(fileName)


def renameFile(src, dst):
    removeFile(dst)
    os.rename(src, dst)


def plotLayers(
        board,
        gerberDirPath,
        useAuxOrigin,
        gerberProtelExtensions,
        layerRenameRules,
        boardProjectName,
):
    targetLayerCount = board.GetCopperLayerCount() + 5
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
        layerId = layers[i][0]
        layerTypeName = layers[i][1]
        pc.SetLayer(layerId)
        pc.OpenPlotfile(layerTypeName, pcbnew.PLOT_FORMAT_GERBER, layerTypeName)
        pc.PlotLayer()
        plotFilePath = pc.GetPlotFileName()

        if len(layerRenameRules) > 0:
            newFileName = layerRenameRules[layerId]
            newFileName = newFileName.replace('[boardProjectName]', boardProjectName)
            newFilePath = '%s/%s' % (gerberDirPath, newFileName)
            renameFile(plotFilePath, newFilePath)
    pc.ClosePlot()


def plotDrill(
        board,
        gerberDirPath,
        boardProjectName,
        excellonFormat,
        useAuxOrigin,
        drillMinimalHeader,
        drillMergeNpth,
        drillExtensionRenameTo,
):
    ew = pcbnew.EXCELLON_WRITER(board)
    ew.SetFormat(True, excellonFormat, 3, 3)
    offset = pcbnew.wxPoint(0,0)
    if useAuxOrigin:
        offset = board.GetAuxOrigin()
    ew.SetOptions(False, drillMinimalHeader, offset, drillMergeNpth)
    ew.CreateDrillandMapFilesSet(gerberDirPath,True,False)
    if drillExtensionRenameTo is not None:
        if drillMergeNpth:
            renameFile('%s/%s.drl' % (gerberDirPath, boardProjectName),
                       '%s/%s.%s' % (gerberDirPath, boardProjectName, drillExtensionRenameTo))
        else:
            renameFile('%s/%s-PTH.drl' % (gerberDirPath, boardProjectName),
                       '%s/%s-PTH.%s' % (gerberDirPath, boardProjectName, drillExtensionRenameTo))
            renameFile('%s/%s-NPTH.drl' % (gerberDirPath, boardProjectName),
                       '%s/%s-NPTH.%s' % (gerberDirPath, boardProjectName, drillExtensionRenameTo))


def createZip(
        pcbServiceName,
        useAuxOrigin,
        excellonFormat,
        gerberProtelExtensions,
        layerRenameRules,
        drillMergeNpth,
        drillExtensionRenameTo,
        drillMinimalHeader
):
    board = pcbnew.GetBoard()
    boardFileName = board.GetFileName()
    boardDirPath = os.path.dirname(boardFileName)
    boardProjectName = (os.path.splitext(os.path.basename(boardFileName)))[0]

    outputDirPath = '%s/%s' % (boardDirPath, outputDirName)
    gerberDirName = '%s_for_%s' % (boardProjectName, pcbServiceName)
    gerberDirPath = '%s/%s' % (outputDirPath, gerberDirName)
    timeStamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    zipFilePath = '%s/%s_%s.zip' % (outputDirPath, timeStamp, gerberDirName)

    if not os.path.exists(outputDirPath):
        os.mkdir(outputDirPath)
    if os.path.exists(gerberDirPath):
        shutil.rmtree(gerberDirPath)
    os.mkdir(gerberDirPath)

    plotLayers(
        board = board,
        gerberDirPath = gerberDirPath,
        useAuxOrigin = useAuxOrigin,
        gerberProtelExtensions = gerberProtelExtensions,
        layerRenameRules = layerRenameRules,
        boardProjectName = boardProjectName,
    )

    plotDrill(
        board = board,
        gerberDirPath = gerberDirPath,
        boardProjectName = boardProjectName,
        excellonFormat = excellonFormat,
        useAuxOrigin = useAuxOrigin,
        drillMinimalHeader = drillMinimalHeader,
        drillMergeNpth = drillMergeNpth,
        drillExtensionRenameTo = drillExtensionRenameTo,
    )

    removeFile(zipFilePath)
    shutil.make_archive(os.path.splitext(zipFilePath)[0], 'zip', outputDirPath, gerberDirName)

    return zipFilePath


class GerberToOrderAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Gerber to order"
        self.category = "A descriptive category name"
        self.description = "A plugin to creage zip compressed gerber files to order PCB for Elecrow, FusionPCB or PCBWay."
        self.show_toolbar_button = False
        # self.icon_file_name = os.path.join(os.path.dirname(__file__), 'simple_plugin.png') # Optional, defaults to ""

    def Run(self):
        class Dialog(wx.Dialog):
            def __init__(self, parent):
                wx.Dialog.__init__(self, parent, id=-1, title='Gerber to order')
                self.panel = wx.Panel(self)
                self.description = wx.StaticText(self.panel, wx.ID_ANY, "Export gerber files and zip files.", pos=(10,10))
                self.execbtn = wx.Button(self.panel, wx.ID_ANY, 'Export', pos=(10,30))
                self.clsbtn = wx.Button(self.panel, wx.ID_ANY, 'Close', pos=(100,30))
                self.clsbtn.Bind(wx.EVT_BUTTON, self.OnClose)
                self.execbtn.Bind(wx.EVT_BUTTON, self.OnExec)
            def OnClose(self,e):
                e.Skip()
                self.Close()
            def OnExec(self,e):
                try:
                    zipFiles = []
                    for pcbService in pcbServices:
                        path = createZip(
                            pcbServiceName = pcbService['name'],
                            useAuxOrigin = pcbService['useAuxOrigin'],
                            gerberProtelExtensions = pcbService['gerberProtelExtensions'],
                            excellonFormat = pcbService['excellonFormat'],
                            drillMergeNpth = pcbService['drillMergeNpth'],
                            drillMinimalHeader = pcbService['drillMinimalHeader'],
                            layerRenameRules = pcbService['layerRenameRules'],
                            drillExtensionRenameTo = pcbService['drillExtensionRenameTo'],
                        )
                        zipFiles.append(path)
                    message = ''
                    if len(zipFiles) > 0:
                        message = 'Exported\n'
                        message += '\n'.join(map(lambda path: os.path.basename(path), zipFiles))
                        message += '\nat\n' + os.path.dirname(zipFiles[0])
                    else:
                        message = 'Select some service to export.'
                    wx.MessageBox(message, 'Gerber to order', wx.OK|wx.ICON_INFORMATION)
                except Exception as e:
                    wx.MessageBox('Error: ' + str(e), 'Gerber to order', wx.OK|wx.ICON_INFORMATION)
                e.Skip()
        dialog = Dialog(None)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
