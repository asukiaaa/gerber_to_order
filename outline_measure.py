import pcbnew

class MinMax1DimHolder:
    def __init__(self):
        self.min = None
        self.max = None

    def updateMinMax(self, v):
        self.max = v if self.max is None else max(v, self.max)
        self.min = v if self.min is None else min(v, self.min)

    def getDistanceNm(self):
        return self.max - self.min

    def getDistanceMm(self):
        return self.getDistanceNm() / 1000000

    def getDistanceStr(self):
        return str(self.getDistanceMm()) #.replace('.', 'p')

    def isMinOrMaxNone(self):
        return self.min is None or self.max is None


class MinMax2DimHolder:
    def __init__(self):
        self.x = MinMax1DimHolder()
        self.y = MinMax1DimHolder()

    def updateMinMax(self, point):
        self.x.updateMinMax(point[0])
        self.y.updateMinMax(point[1])


def hasLineOnDegree(targetDegree, angleDegree, angleDegreeStart):
    angleDegreeEnd = angleDegreeStart + angleDegree
    result = False
    if angleDegree > 0:
        result = (angleDegreeStart <= targetDegree and targetDegree <= angleDegreeEnd) or (angleDegreeStart - 360 <= targetDegree and targetDegree <= angleDegreeEnd - 360)
    else:
        result = (angleDegreeEnd <= targetDegree and targetDegree <= angleDegreeStart ) or (angleDegreeEnd + 360 <= targetDegree and targetDegree <= angleDegreeStart + 360)
    # print('check', targetDegree, result)
    # print(angleDegree, angleDegreeStart, angleDegreeEnd)
    return result


def getArcMinMaxPoints(draw):
    pointCenter = draw.GetCenter()
    pointStart = draw.GetArcStart()
    pointEnd = draw.GetArcEnd()
    points = [pointStart, pointEnd]
    radius = draw.GetRadius()
    angleDegreeStart = draw.GetArcAngleStart() / 10
    angleDegree = draw.GetAngle() / 10
    if hasLineOnDegree(0, angleDegree, angleDegreeStart):
       points.append(pcbnew.wxPoint(pointCenter[0]+radius, pointCenter[1]))
    if hasLineOnDegree(90, angleDegree, angleDegreeStart):
       points.append(pcbnew.wxPoint(pointCenter[0], pointCenter[1]+radius))
    if hasLineOnDegree(180, angleDegree, angleDegreeStart):
       points.append(pcbnew.wxPoint(pointCenter[0]-radius, pointCenter[1]))
    if hasLineOnDegree(270, angleDegree, angleDegreeStart):
       points.append(pcbnew.wxPoint(pointCenter[0], pointCenter[1]-radius))
    return points


def getMinMax2DimOfBoard(board):
    minMax2Dim = MinMax2DimHolder()

    for draw in board.GetDrawings():
        if draw.GetLayerName() == 'Edge.Cuts':
            if draw.GetShapeStr() == 'Arc':
                for point in getArcMinMaxPoints(draw):
                    minMax2Dim.updateMinMax(point)
            elif draw.GetShapeStr() == 'circle':
                r = draw.GetRadius()
                center = draw.GetCenter()
                x = center[0]
                y = center[1]
                minMax2Dim.updateMinMax(pcbnew.wxPoint(x + r, y + r))
                minMax2Dim.updateMinMax(pcbnew.wxPoint(x - r, y - r))
            else:
                minMax2Dim.updateMinMax(draw.GetStart())
                minMax2Dim.updateMinMax(draw.GetEnd())

    return minMax2Dim
    if minMax2Dim.x.isMinOrMaxNone() or minMax2Dim.y.isMinOrMaxNone():
        return None
    return (minMax2Dim.x.getDistanceMm(), minMax2Dim.y.getDistanceMm())


def getWidthHeightNmOfBoard(board):
    minMax2Dim = getMinMax2DimOfBoard(board)
    if minMax2Dim.x.isMinOrMaxNone() or minMax2Dim.y.isMinOrMaxNone():
        return None
    return (minMax2Dim.x.getDistanceNm(), minMax2Dim.y.getDistanceNm())


def getWidthHeightMmOfBoard(board):
    minMax2Dim = getMinMax2DimOfBoard(board)
    if minMax2Dim.x.isMinOrMaxNone() or minMax2Dim.y.isMinOrMaxNone():
        return None
    return (minMax2Dim.x.getDistanceMm(), minMax2Dim.y.getDistanceMm())


def createSizeLabelOfBoard(board):
    wh = getWidthHeightMmOfBoard(board)
    return None if wh is None else str(wh[0]) + 'x' + str(wh[1]) + 'mm'
