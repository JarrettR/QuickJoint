#!/usr/bin/env python
"""
Copyright (C) 2017 Jarrett Rainier jrainier@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""
import inkex, os, cmath, simplepath, simplestyle
try:
    from subprocess import Popen, PIPE
    bsubprocess = True
except:
    bsubprocess = False
    
debugEn = False    
def debugMsg(input):
    if debugEn:
        inkex.debug(input)
    
def numlines(path):
    retval = 0
    for elem in path:
        if elem[0] == "L" or elem[0] == "V" or elem[0] == "H" or elem[0] == "Z":
            retval = retval + 1
    return retval
    
def getmnumber(path):
    retval = 0
    for elem in path:
        if elem[0] == "M":
            return retval
            retval = retval + 1
    return retval
    
def getlinenumber(path, side):
    current = -1
    total = 0
    for elem in path:
        if elem[0] == "L" or elem[0] == "V" or elem[0] == "H" or elem[0] == "Z":
            current += 1
        if current == side:
            return total
        total += 1
    return -1

class QuickJoint(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
        self.OptionParser.add_option("-s", "--side",
                        action="store", type="int", 
                        dest="side", default=0,
                        help="Object face to tabify")
        self.OptionParser.add_option("-n", "--numtabs",
                        action="store", type="int", 
                        dest="numtabs", default=1,
                        help="Number of tabs to add")
        self.OptionParser.add_option("-l", "--numslots",
                        action="store", type="int", 
                        dest="numslots", default=1,
                        help="Number of slots to add")
        self.OptionParser.add_option("-t", "--thickness",
                        action="store", type="float", 
                        dest="thickness", default=3.0,
                        help="Material thickness")
        self.OptionParser.add_option("-k", "--kerf",
                        action="store", type="float", 
                        dest="kerf", default=0.14,
                        help="Measured kerf of cutter")
        self.OptionParser.add_option("-u", "--units",
                        action="store", type="string", 
                        dest="units", default="mm",
                        help="Measurement units")
        self.OptionParser.add_option("-e", "--edgefeatures",
                        action="store", type="inkbool", 
                        dest="edgefeatures", default=False,
                        help="Allow tabs to go right to edges")
        self.OptionParser.add_option("-f", "--flipside",
                        action="store", type="inkbool", 
                        dest="flipside", default=False,
                        help="Flip side of lines that tabs are drawn onto")
        self.OptionParser.add_option("-a", "--activetab",
                        action="store", type="string", 
                        dest="activetab", default='',
                        help="Tab or slot menus")
                        
    def to_complex(self, line):
        debugMsg("To complex: ")
        debugMsg(line)
        return complex(line[0], line[1]) 
        
    def get_length(self, line):
        polR, polPhi = cmath.polar(line)
        return polR
        
    def draw_parallel(self, start, guideLine, stepDistance):
        polR, polPhi = cmath.polar(guideLine)
        polR = stepDistance
        return (cmath.rect(polR, polPhi) + start)
        
    def draw_perpendicular(self, start, guideLine, stepDistance, invert = False):
        polR, polPhi = cmath.polar(guideLine)
        polR = stepDistance
        debugMsg(polPhi)
        if invert:  
            polPhi += (cmath.pi / 2)
        else:
            polPhi -= (cmath.pi / 2)
        debugMsg(polPhi)
        debugMsg(cmath.rect(polR, polPhi))
        return (cmath.rect(polR, polPhi) + start)
        
    def draw_box(self, start, guideLine, xDistance, yDistance, kerf):
        polR, polPhi = cmath.polar(guideLine)
        
        #Kerf expansion
        if self.flipside:  
            start -= cmath.rect(kerf, polPhi)
            start -= cmath.rect(kerf, polPhi + (cmath.pi / 2))
        else:
            start -= cmath.rect(kerf, polPhi)
            start -= cmath.rect(kerf, polPhi - (cmath.pi / 2))
            
        lines = []
        lines.append(['M', [start.real, start.imag]])
        
        #Horizontal
        polR = xDistance
        move = cmath.rect(polR + (2 * kerf), polPhi) + start
        lines.append(['L', [move.real, move.imag]])
        start = move
        
        #Vertical
        polR = yDistance
        if self.flipside:  
            polPhi += (cmath.pi / 2)
        else:
            polPhi -= (cmath.pi / 2)
        move = cmath.rect(polR  + (2 * kerf), polPhi) + start
        lines.append(['L', [move.real, move.imag]])
        start = move
        
        #Horizontal
        polR = xDistance
        if self.flipside:  
            polPhi += (cmath.pi / 2)
        else:
            polPhi -= (cmath.pi / 2)
        move = cmath.rect(polR + (2 * kerf), polPhi) + start
        lines.append(['L', [move.real, move.imag]])
        start = move
        
        lines.append(['Z', []])
        
        return lines
    
    def draw_tabs(self, path, line):
        #Male tab creation
            
        if line == 0:
            #todo: wrap around?
            #find edge case where this throws
            #probably an open shape
            throw()
        
        
        start = self.to_complex(path[line - 1][1]) 
        
        #Line is between last and first (closed) nodes
        closePath = False
        if path[line][0] == "Z":
            line = getmnumber(path)
            closePath = True
            
        end = self.to_complex(path[line][1])
        debugMsg(start)
        debugMsg(end)
            
        debugMsg("5-")
        debugMsg(line)
        debugMsg(path[line - 1])
        debugMsg(path[line])
        
        if self.edgefeatures == False:
            segCount = (self.numtabs * 2) 
            drawValley = False
        else:
            segCount = (self.numtabs * 2) - 1
            drawValley = False

        distance = end - start
        debugMsg(distance)
        debugMsg("segCount - " + str(segCount))
        
        try:
            if self.edgefeatures:
                segLength = self.get_length(distance) / segCount
            else:
                segLength = self.get_length(distance) / (segCount + 1)
        except:
            segLength = self.get_length(distance)
        
        debugMsg("segLength - " + str(segLength))
        newLines = []
        
        if self.edgefeatures == False:
            start = self.draw_parallel(start, distance, segLength)
            newLines.append(['L', [start.real, start.imag]])
            debugMsg("Initial - " + str(start))
            
        
        for i in range(segCount):
            if drawValley == True:
                #Vertical
                start = self.draw_perpendicular(start, distance, self.thickness, self.flipside)
                newLines.append(['L', [start.real, start.imag]])
                debugMsg("ValleyV - " + str(start))
                drawValley = False
                #Horizontal
                start = self.draw_parallel(start, distance, segLength)
                newLines.append(['L', [start.real, start.imag]])
                debugMsg("ValleyH - " + str(start))
            else:
                #Vertical
                start = self.draw_perpendicular(start, distance, self.thickness, not self.flipside)
                newLines.append(['L', [start.real, start.imag]])
                debugMsg("HillV - " + str(start))
                drawValley = True
                #Horizontal
                start = self.draw_parallel(start, distance, segLength)
                newLines.append(['L', [start.real, start.imag]])
                debugMsg("HillH - " + str(start))
                
        if closePath:
            newLines.append(['Z', []])
        return newLines
        
    
    def draw_slots(self, path):
        #Female slot creation
        
        start = self.to_complex(path[0][1])
        end = self.to_complex(path[1][1])
        
        if self.edgefeatures == False:
            segCount = (self.numslots * 2) 
        else:
            segCount = (self.numslots * 2) - 1

        distance = end - start
        debugMsg(distance)
        debugMsg("segCount - " + str(segCount))
        
        try:
            if self.edgefeatures:
                segLength = self.get_length(distance) / segCount
            else:
                segLength = self.get_length(distance) / (segCount + 1)
        except:
            segLength = self.get_length(distance)
        
        debugMsg("segLength - " + str(segLength))
        newLines = []
        
        line_style = simplestyle.formatStyle({ 'stroke': '#000000', 'fill': 'none', 'stroke-width': str(self.unittouu('1px')) })
                
        for i in range(segCount):
            if (self.edgefeatures and (i % 2) == 0) or (not self.edgefeatures and (i % 2)):
                newLines = self.draw_box(start, distance, segLength, self.thickness, self.kerf)
                debugMsg(newLines)
                
                slot_id = self.uniqueId('slot')
                g = inkex.etree.SubElement(self.current_layer, 'g', {'id':slot_id})
                
                line_atts = { 'style':line_style, 'id':slot_id+'-inner-close-tab', 'd':simplepath.formatPath(newLines) }
                inkex.etree.SubElement(g, inkex.addNS('path','svg'), line_atts )
                
            #Find next point
            polR, polPhi = cmath.polar(distance)
            polR = segLength
            start = cmath.rect(polR, polPhi) + start
        
    def effect(self):
        self.side  = self.options.side
        self.numtabs  = self.options.numtabs
        self.numslots  = self.options.numslots
        self.thickness = self.unittouu(str(self.options.thickness) + self.options.units)
        self.kerf = self.unittouu(str(self.options.kerf) + self.options.units)
        self.units = self.options.units
        self.edgefeatures = self.options.edgefeatures
        self.flipside = self.options.flipside
        self.activetab = self.options.activetab
        
        for id, node in self.selected.iteritems():
            debugMsg(node)
            if node.tag == inkex.addNS('path','svg'):
                #p = cubicsuperpath.parsePath(node.get('d'))
                p = simplepath.parsePath(node.get('d'))
                
                debugMsg('1')
                debugMsg(p)
                numLines = numlines(p)
                lineNum = getlinenumber(p, self.side % numLines)

                newPath = []
                if self.activetab == '"tabpage"':
                    newPath = self.draw_tabs(p, lineNum)
                    debugMsg('2')
                    debugMsg(p[:lineNum])
                    debugMsg('3')
                    debugMsg(newPath)
                    debugMsg('4')
                    debugMsg( p[lineNum + 1:])
                    finalPath = p[:lineNum] + newPath + p[lineNum + 1:]
                    
                    debugMsg(finalPath)
                    
                    node.set('d',simplepath.formatPath(finalPath))
                elif self.activetab == '"slotpage"':
                    newPath = self.draw_slots(p)
                

if __name__ == '__main__':
    e = QuickJoint()
    e.affect()
