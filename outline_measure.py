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
    # https://docs.kicad.org/doxygen-python/classpcbnew_1_1EDA__SHAPE.html
    pointCenter = draw.GetCenter()
    if hasattr(draw, "GetArcStart"):
       pointStart = draw.GetArcStart()
    else:
       pointStart = draw.GetStart()
    if hasattr(draw, "GetArcEnd"):
       pointEnd = draw.GetArcEnd()
    else:
       pointEnd = draw.GetEnd()
    points = [pointStart, pointEnd]
    radius = draw.GetRadius()
    angleDegreeStart = draw.GetArcAngleStart() / 10
    if hasattr(draw, "GetAngle"):
       angleDegree = draw.GetAngle() / 10
    else:
       angleDegree = draw.GetArcAngle() / 10
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
        if draw.GetClass() in ["DRAWSEGMENT", "PCB_SHAPE"] and draw.GetLayerName() == 'Edge.Cuts':
            if draw.GetShape() == pcbnew.S_ARC:
                for point in getArcMinMaxPoints(draw):
                    minMax2Dim.updateMinMax(point)
            elif draw.GetShape() == pcbnew.S_CIRCLE:
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
