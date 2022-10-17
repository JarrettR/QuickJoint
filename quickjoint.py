
#!/usr/bin/env python
'''
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

'''
import inkex, cmath
from inkex.paths import Path, ZoneClose, Move
from lxml import etree
    
debugEn = False    
def debugMsg(input):
    if debugEn:
        inkex.utils.debug(input)
    
def linesNumber(path):
    retval = -1
    for elem in path:
        debugMsg('linesNumber')
        debugMsg(elem)
        retval = retval + 1
    debugMsg('Number of lines : ' + str(retval))
    return retval

def to_complex(point):
    return complex(point.x, point.y)
    

class QuickJoint(inkex.Effect):
    def add_arguments(self, pars):
        pars.add_argument('-s', '--side', type=int, default=0, help='Object face to tabify')
        pars.add_argument('-n', '--numtabs', type=int, default=1, help='Number of tabs to add')
        pars.add_argument('-l', '--numslots', type=int, default=1, help='Number of slots to add')
        pars.add_argument('-t', '--thickness', type=float, default=3.0, help='Material thickness')
        pars.add_argument('-k', '--kerf', type=float, default=0.14, help='Measured kerf of cutter')
        pars.add_argument('-u', '--units', default='mm', help='Measurement units')
        pars.add_argument('-e', '--edgefeatures', type=inkex.Boolean, default=False, help='Allow tabs to go right to edges')
        pars.add_argument('-f', '--flipside', type=inkex.Boolean, default=False, help='Flip side of lines that tabs are drawn onto')
        pars.add_argument('-a', '--activetab', default='', help='Tab or slot menus')
                        
    def to_complex(self, command, line):
        debugMsg('To complex: ' + command + ' ' + str(line))
       
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
        
        # Kerf is a provided as a positive kerf width. Although tabs
        # need to be made larger by the width of the kerf, slots need
        # to be made narrower instead.
        kerf = -kerf

        if self.flipside:  
            start -= cmath.rect(kerf / 2, polPhi)
            start -= cmath.rect(kerf / 2, polPhi + (cmath.pi / 2))
        else:
            start -= cmath.rect(kerf / 2, polPhi)
            start -= cmath.rect(kerf / 2, polPhi - (cmath.pi / 2))
            
        lines = []
        lines.append(['M', [start.real, start.imag]])
        
        # Horizontal
        polR = xDistance
        move = cmath.rect(polR + kerf, polPhi) + start
        lines.append(['L', [move.real, move.imag]])
        start = move
        
        # Vertical
        polR = yDistance
        if self.flipside:  
            polPhi += (cmath.pi / 2)
        else:
            polPhi -= (cmath.pi / 2)
        move = cmath.rect(polR  + kerf, polPhi) + start
        lines.append(['L', [move.real, move.imag]])
        start = move
        
        # Horizontal
        polR = xDistance
        if self.flipside:  
            polPhi += (cmath.pi / 2)
        else:
            polPhi -= (cmath.pi / 2)
        move = cmath.rect(polR + kerf, polPhi) + start
        lines.append(['L', [move.real, move.imag]])
        start = move
        
        lines.append(['Z', []])
        
        return lines

    def vectorDraw(self, start, lines, vector):
        start = start + vector
        lines.append(['L', [start.real, start.imag]])
        return start

    def draw_tabs(self, path, line):

        # Male tab creation is complicated by kerfs.
        # I refer to this joint as a sequence of tabs and spaces with vertical runs between.
        # Lengths of tabs and spaces must be adjusted by a portion of the kerf width.
        # End tabs and spaces should be adjusted by half a kerf width, center tabs and spaces by a whole kerf width.
        # Since we always have an odd number of segments, this balances the kerf adjustments.

        # Currently this code works withuot edgefeatures but is off by half a kerf width with edge features turned on.

        start = to_complex(path[line])

        closePath = False
        #Line is between last and first (closed) nodes
        end = None
        if isinstance(path[line+1], ZoneClose):
            end = to_complex(path[0])
            closePath = True
        else:
            end = to_complex(path[line+1])

        debugMsg('start')
        debugMsg(start)
        debugMsg('end')
        debugMsg(end)
   
        debugMsg('5-')

        distance = end - start

        # Calculate the number of segments in the tabbed line: all tabs plus spaces.
        if self.edgefeatures:
            segCount = (self.numtabs * 2) - 1
        else:
            segCount = (self.numtabs * 2) + 1

        debugMsg('distance ' + str(distance))
        debugMsg('segCount ' + str(segCount))

        # Calculate vectors for the parallel portion of tab, space, and endspace.
        segment = distance / segCount
        tabLine = self.draw_parallel(segment, segment, self.kerf)
        spaceLine = self.draw_parallel(segment, segment, -self.kerf)
        endspaceLine = self.draw_parallel(segment, segment, - self.kerf/2)

        # Calculate vectors for tabOut and tabIn: perpendicular away and towards baseline
        tabOut = self.draw_perpendicular(0, distance, self.thickness, not self.flipside)
        tabIn = self.draw_perpendicular(0, distance, self.thickness, self.flipside)

        # Count just the tabs and spaces without the end spaces (when not edgeFeature)
        tabSpaceCount = self.numtabs * 2 - 1
        
        # Distance doesn't need kerf adjustment: two parallel lines are the proper
        # distance apart since they're both affected by the same kerf.

        newLines = []
        cursor = start
        debugMsg('Start: ' + str(start))
        
        # When handling first line, need to set M back
        if isinstance(path[line], Move):
            newLines.append(['M', [start.real, start.imag]])
        
        # If we aren't using edge features, add endspace
        if self.edgefeatures == False:
            cursor = self.vectorDraw(cursor, newLines, endspaceLine)
            debugMsg('Cursor after endspace - ' + str(cursor))

        # Starting on a tab, draw tabSpaceCount tabs and spaces.
        drawTab = True;
        for i in range(tabSpaceCount):
            if drawTab == True:
                cursor = self.vectorDraw(cursor, newLines, tabOut)
                cursor = self.vectorDraw(cursor, newLines, tabLine)
                cursor = self.vectorDraw(cursor, newLines, tabIn)
            else:
                cursor = self.vectorDraw(cursor, newLines, spaceLine)
                
            drawTab = ~drawTab

        # If we aren't using edge features, add final endspace
        if self.edgefeatures == False:
            cursor = self.vectorDraw(cursor, newLines, endspaceLine)
            debugMsg('Cursor after endspace - ' + str(cursor))
            
        if closePath:
            newLines.append(['Z', []])
        return newLines
        
    
    def draw_slots(self, path):
        #Female slot creation

        start = to_complex(path[0])
        end = to_complex(path[1])

        if self.edgefeatures:
            segCount = (self.numslots * 2) - 1 
        else:
            segCount = (self.numslots * 2)

        distance = end - start
        debugMsg('distance ' + str(distance))
        debugMsg('segCount ' + str(segCount))
        
        try:
            if self.edgefeatures:
                segLength = self.get_length(distance) / segCount
            else:
                segLength = self.get_length(distance) / (segCount + 1)
        except:
            segLength = self.get_length(distance)
        
        debugMsg('segLength - ' + str(segLength))
        newLines = []
        
        line_style = str(inkex.Style({ 'stroke': '#000000', 'fill': 'none', 'stroke-width': str(self.svg.unittouu('0.1mm')) }))
                
        for i in range(segCount):
            if (self.edgefeatures and (i % 2) == 0) or (not self.edgefeatures and (i % 2)):
                newLines = self.draw_box(start, distance, segLength, self.thickness, self.kerf)
                debugMsg(newLines)
                
                slot_id = self.svg.get_unique_id('slot')
                g = etree.SubElement(self.svg.get_current_layer(), 'g', {'id':slot_id})
                
                line_atts = { 'style':line_style, 'id':slot_id+'-inner-close-tab', 'd':str(Path(newLines)) }
                etree.SubElement(g, inkex.addNS('path','svg'), line_atts )
                
            #Find next point
            polR, polPhi = cmath.polar(distance)
            polR = segLength
            start = cmath.rect(polR, polPhi) + start
        
    def effect(self):
        self.side  = self.options.side
        self.numtabs  = self.options.numtabs
        self.numslots  = self.options.numslots
        self.thickness = self.svg.unittouu(str(self.options.thickness) + self.options.units)
        self.kerf = self.svg.unittouu(str(self.options.kerf) + self.options.units)
        self.units = self.options.units
        self.edgefeatures = self.options.edgefeatures
        self.flipside = self.options.flipside
        self.activetab = self.options.activetab

        for id, node in self.svg.selected.items():
            debugMsg(node)
            debugMsg('1')
            if node.tag == inkex.addNS('path','svg'):
                p = list(node.path.to_superpath().to_segments())
                debugMsg('2')
                debugMsg(p)

                lines = linesNumber(p)
                lineNum = self.side % lines
                debugMsg(lineNum)

                newPath = []
                if self.activetab == 'tabpage':
                    newPath = self.draw_tabs(p, lineNum)
                    debugMsg('2')
                    debugMsg(p[:lineNum])
                    debugMsg('3')
                    debugMsg(newPath)
                    debugMsg('4')
                    debugMsg( p[lineNum + 1:])
                    finalPath = p[:lineNum] + newPath + p[lineNum + 1:]
                    
                    debugMsg(finalPath)
                    
                    node.set('d',str(Path(finalPath)))
                elif self.activetab == 'slotpage':
                    newPath = self.draw_slots(p)

if __name__ == '__main__':
    QuickJoint().run()
