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

isKiCad_7_0 = re.match(r'^7\.0\..*', pcbnew.Version())
isKiCad_7_0_orMore = isKiCad_7_0 is not None

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
        # https://support.jlcpcb.com/article/22-how-to-generate-the-gerber-files
        # https://support.jlcpcb.com/article/149-how-to-generate-gerber-and-drill-files-in-kicad
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
    targetLayerCount = board.GetCopperLayerCount() + 5
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
    offset = pcbnew.VECTOR2I(0,0) if isKiCad_7_0_orMore else pcbnew.wxPoint(0,0)
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

    return zipFilePath


class Dialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, id=-1, title=pluginName)
        panel = wx.Panel(self)
        description = wx.StaticText(panel, label='Export gerber and zip files.')
        execbtn = wx.Button(panel, label='Export')
        clsbtn = wx.Button(panel, label='Close')
        clsbtn.Bind(wx.EVT_BUTTON, self.OnClose)
        execbtn.Bind(wx.EVT_BUTTON, self.OnExec)
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(execbtn)
        buttonSizer.Add(clsbtn)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(description, flag=wx.EXPAND|wx.BOTTOM|wx.TOP|wx.LEFT, border=5)
        layout.Add(buttonSizer, flag=wx.EXPAND|wx.LEFT, border=5)
        panel.SetSizer(layout)

    def OnClose(self,e):
        e.Skip()
        self.Close()

    def OnExec(self,e):
        try:
            zipFiles = []
            sizeLabel = createSizeLabelOfBoard(pcbnew.GetBoard())
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
                    sizeLabel = sizeLabel,
                )
                zipFiles.append(path)
            message = ''
            if len(zipFiles) > 0:
                message = 'Exported\n'
                message += '\n'.join(map(lambda path: os.path.basename(path), zipFiles))
                message += '\nat\n' + os.path.dirname(zipFiles[0])
            else:
                message = 'Select some service to export.'
            wx.MessageBox(message, pluginName, wx.OK|wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox('Error: ' + str(e) + '\n\n' + traceback.format_exc(), pluginName, wx.OK|wx.ICON_INFORMATION)
        e.Skip()


class GerberToOrderAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = pluginName
        self.category = 'A descriptive category name'
        self.description = 'A plugin to creage zip compressed gerber files to order PCB for Elecrow, FusionPCB, PCBWay or JLCPCB.'
        self.show_toolbar_button = False
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'gerber_to_order.png')

    def Run(self):
        dialog = Dialog(None)
        dialog.Center()
        dialog.ShowModal()
        dialog.Destroy()
