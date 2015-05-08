from AppKit import NSImage
from robofab.pens.pointPen import AbstractPointPen
from lib.UI.toolbarGlyphTools import ToolbarGlyphTools
from mojo.events import addObserver
import math
import os

def getLength((x1, y1), (x2, y2)):
	return math.sqrt((x2-x1)**2 + (y2-y1)**2)

def pointOnACurve(((x1, y1), (cx1, cy1), (cx2, cy2), (x2, y2)), value):
	dx = x1
	cx = (cx1 - dx) * 3.0
	bx = (cx2 - cx1) * 3.0 - cx
	ax = x2 - dx - cx - bx

	dy = y1
	cy = (cy1 - dy) * 3.0
	by = (cy2 - cy1) * 3.0 - cy
	ay = y2 - dy - cy - by

	mx = ax*(value)**3 + bx*(value)**2 + cx*(value) + dx
	my = ay*(value)**3 + by*(value)**2 + cy*(value) + dy

	return mx, my
		
class AddOverlapPointPen(AbstractPointPen):
	
	offset = 30
	
	def __init__(self, selectedPoints=[]):
		self.selectedPoints = selectedPoints
		
		self._contours = []
		self._components = []
	
	def beginPath(self):
		self._contours.append([])
		self.firstSegment = None
		self.prevOncurve = None
	
	def addPoint(self, (x, y), segmentType=None, smooth=False, name=None, **kwargs):
		data = dict(point=(x, y), segmentType=segmentType, smooth=smooth, name=name, kwargs=kwargs)
		self._contours[-1].append(data) 
	 
	def endPath(self):
		pass
	
	def addComponent(self, baseGlyphName, transformation):
		pass
	
	def _offset(self, (x1, y1), (x2, y2)):
		length = getLength((x1, y1), (x2, y2))
		if length == 0:
			return 0, 0
		ox = (x2-x1)/length*self.offset
		oy = (y2-y1)/length*self.offset
		return int(round(ox)), int(round(oy))
	
	def drawPoints(self, outpen):
		for pointsData in self._contours:
			if len(pointsData) == 1:
				# ignore single movetos and anchors
				continue
			outpen.beginPath()
			lenPointsData = len(pointsData)
			for i, pointData in enumerate(pointsData):
				currentPoint = pointData["point"]
				addExtraPoint = None
				if pointData["segmentType"] and pointData["point"] in self.selectedPoints:
					prevPointData = pointsData[i-1]
					nextPointData = pointsData[(i+1) % lenPointsData]
					
					prevOffsetX, prevOffsetY = self._offset(prevPointData["point"], pointData["point"])
					nextOffsetX, nextOffsetY = self._offset(pointData["point"], nextPointData["point"])
					
					if (nextOffsetX, nextOffsetY) == (0, 0) and nextPointData["segmentType"] is None:
						nextSegment = [
							pointsData[(i+3) % lenPointsData]["point"], 
							pointsData[(i+2) % lenPointsData]["point"], 
							nextPointData["point"], 
							pointData["point"]
							]
						newPoint = pointOnACurve(nextSegment, 0.9)
						nextOffsetX, nextOffsetY = self._offset(pointData["point"], newPoint)
					addExtraPoint = currentPoint[0] - nextOffsetX, currentPoint[1] - nextOffsetY
					
					if (prevOffsetX, prevOffsetY) == (0, 0) and prevPointData["segmentType"] is None:
						prevSegment = [
							pointsData[i-3]["point"], 
							pointsData[i-2]["point"], 
							prevPointData["point"], 
							pointData["point"]
							]
						newPoint = pointOnACurve(prevSegment, 0.9)
						prevOffsetX, prevOffsetY = self._offset(newPoint, pointData["point"])
					currentPoint = currentPoint[0] + prevOffsetX, currentPoint[1] + prevOffsetY
					
				outpen.addPoint(currentPoint,
					pointData["segmentType"],
					pointData["smooth"],
					pointData["name"],
					**pointData["kwargs"]
					)
					
				if addExtraPoint:
					outpen.addPoint(addExtraPoint, "line")
					
			outpen.endPath()
			
		for baseGlyphName, transformation in self._components:
			outpen.addComponent(baseGlyphName, transformation)


class AddOverlapTool(object):
		
	base_path = os.path.dirname(__file__)
	
	def __init__(self):
		
		addObserver(self, "addOverlapToolbarItem", "glyphWindowWillShowToolbarItems")

	def addOverlapToolbarItem(self, info):
		
		toolbarItems = info['toolbarItems']
		
		label = 'Add Overlap'
		identifier = 'addOverlap'
		filename = 'AddOverlapButton.pdf'
		callback = self.addOverlap
		index=-2
		
		imagePath = os.path.join(self.base_path, 'resources', filename)
		image = NSImage.alloc().initByReferencingFile_(imagePath)
		
		view = ToolbarGlyphTools((30, 25), 
			[dict(image=image, toolTip=label)], trackingMode="one")
		
		newItem = dict(itemIdentifier=identifier,
			label = label,
			callback = callback,
			view = view
		)
		
		toolbarItems.insert(index, newItem)
	
	def addOverlap(self, sender):
		
		g = CurrentGlyph()
		
		selection = []
		
		for p in g.selection:
			p.selected = False
			selection.append((p.x, p.y))
			
		pen = AddOverlapPointPen(selection)
		
		g.drawPoints(pen)
		
		g.prepareUndo("addOverlap")
		g.clearContours()
		
		pen.drawPoints(g.getPointPen())
		
		g.performUndo()
		g.update()

AddOverlapTool()