from AppKit import NSImage
from robofab.pens.pointPen import AbstractPointPen
from lib.UI.toolbarGlyphTools import ToolbarGlyphTools
from mojo.events import addObserver
import math
import os

def getLength((x1, y1), (x2, y2)):
	return math.sqrt((x2-x1)**2 + (y2-y1)**2)

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
				if pointData["point"] in self.selectedPoints:
					prevPointData = pointsData[i-1]
					nextPointData = pointsData[(i+1) % lenPointsData]
					
					prevOffsetX, prevOffsetY = self._offset(prevPointData["point"], pointData["point"])
					nextOffsetX, nextOffsetY = self._offset(pointData["point"], nextPointData["point"])
					
					addExtraPoint = pointData["point"][0] - nextOffsetX, pointData["point"][1] - nextOffsetY
					
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
		
		addObserver(self, "addOverlapToolbar", "glyphWindowDidOpen")

	def addOverlapToolbar(self, info):
		window = info['window']
		
		if window is None:
			return
		
		label = 'Add Overlap'
		identifier = 'overlapTool'
		filename = 'toolbarAddOverlap.pdf'
		callback = self.addOverlap
		index=-2
		
		toolbarItems = window.getToolbarItems()
		vanillaWindow = window.window()
		displayMode = vanillaWindow._window.toolbar().displayMode()
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
		vanillaWindow.addToolbar(toolbarIdentifier="toolbar-%s" % identifier, 
			toolbarItems=toolbarItems, 
			addStandardItems=False)
		vanillaWindow._window.toolbar().setDisplayMode_(displayMode)
	
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