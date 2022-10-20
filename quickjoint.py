
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
        pars.add_argument('-f', '--flipside', type=inkex.Boolean, default=False, help='Flip side of lines that tabs are drawn onto')
        pars.add_argument('-a', '--activetab', default='', help='Tab or slot menus')
        pars.add_argument('-S', '--featureStart', type=inkex.Boolean, default=False, help='Tab/slot instead of space on the start edge')
        pars.add_argument('-E', '--featureEnd', type=inkex.Boolean, default=False, help='Tab/slot instead of space on the end edge')
                        
    def to_complex(self, command, line):
        debugMsg('To complex: ' + command + ' ' + str(line))
       
        return complex(line[0], line[1]) 
        
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

    def move(self, lines, point):
        debugMsg("- move: " + str(point))
        lines.append(['M', [point.real, point.imag]])
        
    def line(self, lines, point):
        debugMsg("- line: " + str(point))
        lines.append(['L', [point.real, point.imag]])
        
    def draw_box(self, start, lengthVector, height, kerf):

        # Kerf is a provided as a positive kerf width. Although tabs
        # need to be made larger by the width of the kerf, slots need
        # to be made narrower instead, since the cut widens them.

        # Calculate kerfed height and length vectors
        heightEdge = self.draw_perpendicular(0, lengthVector, height - kerf, self.flipside)
        lengthEdge = self.draw_parallel(lengthVector, lengthVector, -kerf)
        
        debugMsg("draw_box; lengthEdge: " + str(lengthEdge) + ", heightEdge: " + str(heightEdge))
        
        cursor = self.draw_parallel(start, lengthEdge, kerf/2)
        cursor = self.draw_perpendicular(cursor, heightEdge, kerf/2)
        
        lines = []
        self.move(lines, cursor)
        
        cursor += lengthEdge
        self.line(lines, cursor)
        
        cursor += heightEdge
        self.line(lines, cursor)
        
        cursor -= lengthEdge
        self.line(lines, cursor)

        cursor -= heightEdge
        self.line(lines, cursor)
        
        lines.append(['Z', []])
        
        return lines

    def vectorDraw(self, start, lines, vector):
        start = start + vector
        self.draw(lines, start)
        return start

    def draw_tabs(self, path, line):
        # Male tab creation is complicated by kerfs.
        # For the tab creation code: the joint is a sequence of tabs and spaces with perpendicular shifts between them.
        # The lengths of tabs and spaces must be adjusted by a portion of the kerf width, but the depth does not.
        # Tabs should be longer and spaces should be shorter, since the kerf reduces the width of each tab.
        # End tabs and spaces should be adjusted by half a kerf width, center tabs and spaces by a whole kerf width.
        # Since we always have an odd number of segments, this balances the kerf adjustments.
        start = to_complex(path[line])

        closePath = False
        #Line is between last and first (closed) nodes
        end = None
        if isinstance(path[line+1], ZoneClose):
            end = to_complex(path[0])
            closePath = True
        else:
            end = to_complex(path[line+1])

        debugMsg('start: ' + str(start) + "; end: " + str(end))

        distance = end - start

        # Calculate the number of segments in the tabbed line: all tabs plus spaces.
        segCount = self.numtabs * 2 - 1
        if not self.featureStart: segCount = segCount + 1
        if not self.featureEnd: segCount = segCount + 1
        
        debugMsg('distance: ' + str(distance))
        debugMsg('segCount: ' + str(segCount))

        # Calculate vectors for the parallel portion of tab, space, and endspace.
        segment = distance / segCount
        tabLine = self.draw_parallel(segment, segment, self.kerf)
        endtabLine = self.draw_parallel(segment, segment, self.kerf/2)
        spaceLine = self.draw_parallel(segment, segment, -self.kerf)
        endspaceLine = self.draw_parallel(segment, segment, - self.kerf/2)

        # Calculate vectors for tabOut and tabIn: perpendicular away and towards baseline
        tabOut = self.draw_perpendicular(0, distance, self.thickness, not self.flipside)
        tabIn = self.draw_perpendicular(0, distance, self.thickness, self.flipside)

        drawTab = self.featureStart
        newLines = []
        cursor = start

        # When handling first line, need to set M back
        if isinstance(path[line], Move):
            newLines.append(['M', [start.real, start.imag]])
        else:
            newLines.append(['L', [start.real, start.imag]])
            
        for i in range(segCount):
            debugMsg("i = " + str(i))
            if i == 0 or i == segCount - 1:
                if drawTab == True:
                    debugMsg("- end tab")
                    cursor = self.vectorDraw(cursor, newLines, tabOut)
                    cursor = self.vectorDraw(cursor, newLines, endtabLine)
                    cursor = self.vectorDraw(cursor, newLines, tabIn)
                else:
                    debugMsg("- end space")
                    cursor = self.vectorDraw(cursor, newLines, endspaceLine)
            else:
                if drawTab == True:
                    debugMsg("- tab")
                    cursor = self.vectorDraw(cursor, newLines, tabOut)
                    cursor = self.vectorDraw(cursor, newLines, tabLine)
                    cursor = self.vectorDraw(cursor, newLines, tabIn)
                else:
                    debugMsg("- space")
                    cursor = self.vectorDraw(cursor, newLines, spaceLine)
            drawTab = not drawTab

        if closePath:
            newLines.append(['Z', []])
        return newLines
        
    def add_new_path_from_lines(self, lines, line_style):
        slot_id = self.svg.get_unique_id('slot')
        g = etree.SubElement(self.svg.get_current_layer(), 'g', {'id':slot_id})

        line_atts = { 'style':line_style, 'id':slot_id+'-inner-close-tab', 'd':str(Path(lines)) }
        etree.SubElement(g, inkex.addNS('path','svg'), line_atts )

    def draw_slots(self, path):
        # Female slot creation
        start = to_complex(path[0])
        end = to_complex(path[1])

        # Total number of segments including all slots and spaces
        segCount = self.numslots * 2 - 1
        if not self.featureStart: segCount = segCount + 1
        if not self.featureEnd: segCount = segCount + 1
        
        distance = end - start
        debugMsg('distance ' + str(distance))
        debugMsg('segCount ' + str(segCount))

        segVector = distance / segCount
        newLines = []
        line_style = str(inkex.Style({ 'stroke': '#000000', 'fill': 'none', 'stroke-width': str(self.svg.unittouu('0.1mm')) }))
        drawSlot = self.featureStart
        cursor = start
        for i in range(segCount):
            if drawSlot:
                self.add_new_path_from_lines(self.draw_box(cursor, segVector, self.thickness, self.kerf), line_style)
            cursor = cursor + segVector
            drawSlot = not drawSlot
            debugMsg("i: " + str(i) + ", cursor: " + str(cursor))
        
    def effect(self):
        self.side  = self.options.side
        self.numtabs  = self.options.numtabs
        self.numslots  = self.options.numslots
        self.thickness = self.svg.unittouu(str(self.options.thickness) + self.options.units)
        self.kerf = self.svg.unittouu(str(self.options.kerf) + self.options.units)
        self.units = self.options.units
        self.featureStart = self.options.featureStart
        self.featureEnd = self.options.featureEnd
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
