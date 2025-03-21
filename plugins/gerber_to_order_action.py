import pcbnew
import os
import traceback
import glob
import time
import shutil
import wx
import locale
import zipfile
# import datetime
from .outline_measure import createSizeLabelOfBoard
import re

pluginName = 'Gerber to order'
outputDirName = 'gerber_to_order'
retryCount = 10
retryWaitSecond = 0.1

versionRegrepResult = re.compile("^([0-9]*)\.([0-9]*)\..*").match(pcbnew.Version())
versionMajor = int(versionRegrepResult.group(1))
# versionMinor = int(versionRegrepResult.group(2))
isKiCad_7_orMore = versionMajor >= 7

layers = [
    [ pcbnew.F_Cu,      'F_Cu' ],
    [ pcbnew.B_Cu,      'B_Cu' ],
    [ pcbnew.F_SilkS,   'F_Silks' ],
    [ pcbnew.B_SilkS,   'B_Silks' ],
    [ pcbnew.F_Mask,    'F_Mask' ],
    [ pcbnew.B_Mask,    'B_Mask' ],
    [ pcbnew.F_Paste,   'F_Paste' ],
    [ pcbnew.B_Paste,   'B_Paste' ],
    [ pcbnew.Edge_Cuts, 'Edge_Cuts' ],
    [ pcbnew.In1_Cu,    'In1_Cu' ],
    [ pcbnew.In2_Cu,    'In2_Cu' ],
    [ pcbnew.In3_Cu,    'In3_Cu' ],
    [ pcbnew.In4_Cu,    'In4_Cu' ],
]

pcbServices = [
    {
        'name': 'Default',
        'useAuxOrigin': False,
        'gerberProtelExtensions': False,
        'excellonFormat': pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT,
        'drillMergeNpth': False,
        'drillMinimalHeader': False,
        'layerRenameRules': {},
        'drillExtensionRenameTo': None,
    },
    {
        # https://www.elecrow.com/pcb-manufacturing.html
        'name': 'Elecrow',
        'useAuxOrigin': True,
        'gerberProtelExtensions': False,
        'excellonFormat': pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT,
        'drillMergeNpth': False,
        'drillMinimalHeader': False,
        'layerRenameRules': {
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
        'drillExtensionRenameTo': 'TXT',
    },
    {
        # https://wiki.seeedstudio.com/Service_for_Fusion_PCB/
        # http://support.seeedstudio.com/knowledgebase/articles/1824574-how-to-generate-gerber-and-drill-files-from-kicad
        'name': 'FusionPCB',
        'useAuxOrigin': True,
        'gerberProtelExtensions': True,
        'excellonFormat': pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT,
        'drillMergeNpth': True,
        'drillMinimalHeader': False,
        'layerRenameRules': {
            pcbnew.F_Cu:      '[boardProjectName].GTL',
            pcbnew.B_Cu:      '[boardProjectName].GBL',
            pcbnew.F_SilkS:   '[boardProjectName].GTO',
            pcbnew.B_SilkS:   '[boardProjectName].GBO',
            pcbnew.F_Mask:    '[boardProjectName].GTS',
            pcbnew.B_Mask:    '[boardProjectName].GBS',
        },
        'drillExtensionRenameTo': 'TXT',
    },
    {
        # https://www.pcbway.com/blog/help_center/Generate_Gerber_file_from_Kicad.html
        'name': 'PCBWay',
        'useAuxOrigin': True,
        'gerberProtelExtensions': False,
        'excellonFormat': pcbnew.EXCELLON_WRITER.SUPPRESS_LEADING,
        'drillMergeNpth': False,
        'drillMinimalHeader': True,
        'layerRenameRules': {
            pcbnew.F_Cu:      '[boardProjectName].GTL',
            pcbnew.B_Cu:      '[boardProjectName].GBL',
            pcbnew.F_SilkS:   '[boardProjectName].GTO',
            pcbnew.B_SilkS:   '[boardProjectName].GBO',
            pcbnew.F_Mask:    '[boardProjectName].GTS',
            pcbnew.B_Mask:    '[boardProjectName].GBS',
            pcbnew.Edge_Cuts: '[boardProjectName].GML',
        },
        'drillExtensionRenameTo': 'TXT',
    },
    {
        # https://jlcpcb.com/help/article/suggested-naming-patterns
        # https://jlcpcb.com/help/article/how-to-generate-gerber-and-drill-files-in-kicad-8
        'name': 'JLCPCB',
        'useAuxOrigin': False,
        'gerberProtelExtensions': True,
        'excellonFormat': pcbnew.EXCELLON_WRITER.DECIMAL_FORMAT,
        'drillMergeNpth': False,
        'drillMinimalHeader': False,
        'layerRenameRules': {
            pcbnew.F_Cu:      '[boardProjectName].GTL',
            pcbnew.B_Cu:      '[boardProjectName].GBL',
            pcbnew.F_SilkS:   '[boardProjectName].GTO',
            pcbnew.B_SilkS:   '[boardProjectName].GBO',
            pcbnew.F_Mask:    '[boardProjectName].GTS',
            pcbnew.B_Mask:    '[boardProjectName].GBS',
            pcbnew.F_Paste:   '[boardProjectName].GTP',
            pcbnew.B_Paste:   '[boardProjectName].GBP',
            pcbnew.Edge_Cuts: '[boardProjectName].GKO',
            pcbnew.In1_Cu:    '[boardProjectName].GL2',
            pcbnew.In2_Cu:    '[boardProjectName].GL3',
        },
        'drillExtensionRenameTo': 'TXT',
    },
]


def removeFileIfExists(fileNameWildCard, retryRemainingCount = retryCount):
    for fileName in glob.glob(fileNameWildCard):
        if os.path.exists(fileName):
            os.remove(fileName)
            while (os.path.exists(fileName) and retryRemainingCount > 0):
                time.sleep(retryWaitSecond)
                retryRemainingCount -= 1


def renameFileIfExists(src, dst):
    if os.path.exists(src):
        renameFile(src, dst)


def renameFile(src, dst, retryRemainingCount = retryCount):
    try:
        removeFileIfExists(dst)
        os.rename(src, dst)
    except Exception:
        if retryRemainingCount > 0:
            time.sleep(retryWaitSecond)
            renameFile(src, dst, retryRemainingCount-1)
        else:
            raise Exception('Cannot rename %s to %s' % (src, dst))


def removeDirIfExists(dirPathWildCard, retryRemainingCount = retryCount):
    for dirPath in glob.glob(dirPathWildCard):
        if os.path.exists(dirPath):
            shutil.rmtree(dirPath)
            while (os.path.exists(dirPath) and retryRemainingCount > 0):
                time.sleep(retryWaitSecond)
                retryRemainingCount -= 1


def makeDir(dirPath, retryRemainingCount = retryCount):
    os.mkdir(dirPath)
    while (not os.path.exists(dirPath) and retryRemainingCount > 0):
        time.sleep(retryWaitSecond)
        retryRemainingCount -= 1


def plotLayers(
        board,
        gerberDirPath,
        useAuxOrigin,
        gerberProtelExtensions,
        layerRenameRules,
        boardProjectName,
):
    targetLayerCount = board.GetCopperLayerCount() + 7
    pc = pcbnew.PLOT_CONTROLLER(board)
    po = pc.GetPlotOptions()

    po.SetOutputDirectory(gerberDirPath)
    po.SetPlotValue(True)
    po.SetPlotReference(True)
    if hasattr(po, "SetExcludeEdgeLayer"):
        po.SetExcludeEdgeLayer(True)
    if hasattr(po, "SetLineWidth"):
        po.SetLineWidth(pcbnew.FromMM(0.1))
    else:
        po.SetSketchPadLineWidth(pcbnew.FromMM(0.1))
    po.SetSubtractMaskFromSilk(False)
    po.SetUseAuxOrigin(useAuxOrigin)
    po.SetUseGerberProtelExtensions(gerberProtelExtensions)
    if hasattr(pcbnew, "PCB_PLOT_PARAMS.NO_DRILL_SHAPE"):
        po.SetDrillMarksType(pcbnew.PCB_PLOT_PARAMS.NO_DRILL_SHAPE)
    po.SetSkipPlotNPTH_Pads(False)

    plotFiles = []
    for i in range(targetLayerCount):
        layerId = layers[i][0]
        layerTypeName = layers[i][1]
        pc.SetLayer(layerId)
        pc.OpenPlotfile(layerTypeName, pcbnew.PLOT_FORMAT_GERBER, layerTypeName)
        pc.PlotLayer()
        plotFiles.append(pc.GetPlotFileName())
    pc.ClosePlot()

    if len(layerRenameRules) > 0:
        for i in range(targetLayerCount):
            plotFilePath = plotFiles[i]
            layerId = layers[i][0]
            if layerId in layerRenameRules:
                newFileName = layerRenameRules[layerId]
                newFileName = newFileName.replace('[boardProjectName]', boardProjectName)
                newFilePath = '%s/%s' % (gerberDirPath, newFileName)
                renameFile(plotFilePath, newFilePath)


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
    offset = pcbnew.VECTOR2I(0,0) if isKiCad_7_orMore else pcbnew.wxPoint(0,0)
    if useAuxOrigin:
        if hasattr(board, "GetAuxOrigin"):
            offset = board.GetAuxOrigin()
        else:
            offset = board.GetDesignSettings().GetAuxOrigin()
    ew.SetOptions(False, drillMinimalHeader, offset, drillMergeNpth)
    ew.CreateDrillandMapFilesSet(gerberDirPath,True,False)
    if drillExtensionRenameTo is not None:
        if drillMergeNpth:
            renameFileIfExists('%s/%s.drl' % (gerberDirPath, boardProjectName),
                               '%s/%s.%s' % (gerberDirPath, boardProjectName, drillExtensionRenameTo))
        else:
            renameFileIfExists('%s/%s-PTH.drl' % (gerberDirPath, boardProjectName),
                               '%s/%s-PTH.%s' % (gerberDirPath, boardProjectName, drillExtensionRenameTo))
            renameFileIfExists('%s/%s-NPTH.drl' % (gerberDirPath, boardProjectName),
                               '%s/%s-NPTH.%s' % (gerberDirPath, boardProjectName, drillExtensionRenameTo))


def createZip(
        pcbServiceName,
        useAuxOrigin,
        excellonFormat,
        gerberProtelExtensions,
        layerRenameRules,
        drillMergeNpth,
        drillExtensionRenameTo,
        drillMinimalHeader,
        sizeLabel,
        keepGerbers,
):
    board = pcbnew.GetBoard()
    boardFileName = board.GetFileName()
    boardDirPath = os.path.dirname(boardFileName)
    boardProjectName = (os.path.splitext(os.path.basename(boardFileName)))[0]

    outputDirPath = '%s/%s' % (boardDirPath, outputDirName)
    gerberDirNameWildCard = '%s' % boardProjectName
    gerberDirName = '%s' % boardProjectName
    if sizeLabel is not None:
        gerberDirName += '_' + sizeLabel
    gerberDirNameWildCard += '*'
    gerberDirName += '_for_' + pcbServiceName
    gerberDirNameWildCard += '_for_' + pcbServiceName
    gerberDirPath = '%s/%s' % (outputDirPath, gerberDirName)
    gerberDirPathWildCard = '%s/%s' % (outputDirPath, gerberDirNameWildCard)
    # timeStamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    # zipFilePath = '%s/%s_%s.zip' % (outputDirPath, timeStamp, gerberDirName)
    zipFilePath = '%s/%s.zip' % (outputDirPath, gerberDirName)
    zipFilePathWildCard = '%s/%s.zip' % (outputDirPath, gerberDirNameWildCard)

    if not os.path.exists(outputDirPath):
        makeDir(outputDirPath)
    removeDirIfExists(gerberDirPathWildCard)
    makeDir(gerberDirPath)

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

    removeFileIfExists(zipFilePathWildCard)
    shutil.make_archive(os.path.splitext(zipFilePath)[0], 'zip', outputDirPath, gerberDirName)

    if not keepGerbers:
        removeDirIfExists(gerberDirPathWildCard)

    return zipFilePath


class Dialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Export Options")
        sizerVertical = wx.BoxSizer(wx.VERTICAL|wx.EXPAND)
        manufacturer_choices = ["All manufacturers"] + [service["name"] for service in pcbServices]
        self.manufacturer = wx.RadioBox(self, label="Select manufacturer to export", choices=manufacturer_choices, style=wx.RA_VERTICAL)
        sizerVertical.Add(self.manufacturer, flag=wx.LEFT|wx.RIGHT|wx.EXPAND, border=10)
        self.keepGerbers = wx.CheckBox(self, label="Keep folder(s) with gerbers layers")
        sizerVertical.Add(self.keepGerbers, flag=wx.LEFT|wx.RIGHT|wx.EXPAND, border=10)
        btnExport = wx.Button(self, label="Export")
        btnCancel = wx.Button(self, label="Cancel")
        btnExport.SetDefault()
        btnExport.Bind(wx.EVT_BUTTON, self.OnExec)
        btnCancel.Bind(wx.EVT_BUTTON, self.OnClose)
        sizerButtons = wx.BoxSizer(wx.HORIZONTAL)
        sizerButtons.Add(btnExport, flag=wx.RIGHT, border=5)
        sizerButtons.Add(btnCancel)
        sizerVertical.Add(sizerButtons, flag=wx.ALIGN_CENTER|wx.ALL, border=10)
        self.SetSizerAndFit(sizerVertical)

    def OnClose(self,e):
        e.Skip()
        self.Close()

    def OnExec(self,e):
        try:
            zipFiles = []
            sizeLabel = createSizeLabelOfBoard(pcbnew.GetBoard())
            keepGerbers = self.keepGerbers.GetValue()
            if self.manufacturer.GetSelection() == 0:
                pcbServicesToProcess = pcbServices
            else:
                pcbServicesToProcess = [pcbServices[self.manufacturer.GetSelection()-1]]
            for pcbService in pcbServicesToProcess:
                path = createZip(
                    pcbServiceName = pcbService['name'],
                    useAuxOrigin = pcbService['useAuxOrigin'],
                    gerberProtelExtensions = pcbService['gerberProtelExtensions'],
                    excellonFormat = pcbService['excellonFormat'],
                    drillMergeNpth = pcbService['drillMergeNpth'],
                    drillMinimalHeader = pcbService['drillMinimalHeader'],
                    layerRenameRules = pcbService['layerRenameRules'],
                    drillExtensionRenameTo = pcbService['drillExtensionRenameTo'],
                    sizeLabel = sizeLabel,
                    keepGerbers = keepGerbers
                )
                zipFiles.append(path)
            if len(zipFiles) > 0:
                wx.LaunchDefaultApplication(os.path.dirname(zipFiles[0]))
            else:
                wx.MessageBox('Select some service to export.', pluginName, wx.OK|wx.ICON_INFORMATION)
            self.Close()
        except Exception as e:
            wx.MessageBox('Error: ' + str(e) + '\n\n' + traceback.format_exc(), pluginName, wx.OK|wx.ICON_INFORMATION)
        e.Skip()


class GerberToOrderAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = pluginName
        self.category = 'A descriptive category name'
        self.description = 'A plugin to creage zip compressed gerber files to order PCB for Elecrow, FusionPCB, PCBWay or JLCPCB.'
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'gerber_to_order.png')

    def Run(self):
        dialog = Dialog(None)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
