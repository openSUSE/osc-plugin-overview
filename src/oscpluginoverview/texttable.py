#!/usr/bin/env python
#
# Copyright (C) 2003 Gerome Fournier <jefke(at)free.fr>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""module for creating simple ASCII tables


Example:

    table = Texttable()
    table.set_cols_align(["l", "r", "c"])
    table.set_cols_valign(["t", "m", "b"])
    table.add_rows([ ["Name", "Age", "Nickname"],
                     ["Mr\\nXavier\\nHuon", 32, "Xav'"],
                     ["Mr\\nBaptiste\\nClement", 1, "Baby"] ])
    print table.draw()

Result:

    +----------+-----+----------+
    |   Name   | Age | Nickname |
    +==========+=====+==========+
    | Mr       |     |          |
    | Xavier   |  32 |          |
    | Huon     |     |   Xav'   |
    +----------+-----+----------+
    | Mr       |     |          |
    | Baptiste |   1 |          |
    | Clement  |     |   Baby   |
    +----------+-----+----------+
"""

__all__ = ["Texttable", "ArraySizeError"]

__author__ = 'Gerome Fournier <jefke(at)free.fr>'
__license__ = 'GPL'
__version__ = '0.6'
__revision__ = '$Id: texttable.py,v 1.9 2003/10/30 18:31:28 jef Exp jef $'
__credits__ = """\
Jeff Kowalczyk:
    - textwrap improved import
    - comment concerning header output

Anonymous:
    - add_rows method, for adding rows in one go
"""

import sys
import os
import string

try:
    if sys.version >= '2.3':
        import textwrap
    elif sys.version >= '2.2':
        from optparse import textwrap
    else:
        from optik import textwrap
except ImportError:
    sys.stderr.write("Can't import textwrap module!\n")
    raise

try:
    True, False
except NameError:
    (True, False) = (1, 0)

def getTerminalWidth():
    rows, columns = os.popen('stty size', 'r').read().split()
    return int( columns )

class ArraySizeError(Exception):
    """Exception raised when specified rows don't fit the required size
    """

    def __init__(self, msg):
        self.msg = msg
        Exception.__init__(self, msg, '')

    def __str__(self):
        return self.msg

class Texttable:

    BORDER = 1
    HEADER = 1 << 1
    HLINES = 1 << 2
    VLINES = 1 << 3

    _attr_val = {
      'R':'\033[0;31m',
      'G':'\033[0;32m',
      'B':'\033[0;34m',
      'C':'\033[0;36m',
      'M':'\033[0;35m',
      'Y':'\033[0;33m',
      None:'\033[0m'
    }

    def __init__(self, max_width=getTerminalWidth()):
        """Constructor

        - max_width is an integer, specifying the maximum width of the table
        - if set to 0, size is unlimited, therefore cells won't be wrapped
        """

        if max_width <= 0:
            max_width = False
        self._max_width = max_width
        self._deco = Texttable.VLINES | Texttable.HLINES | Texttable.BORDER | \
            Texttable.HEADER
        self.set_chars(['-', '|', '+', '='])
        self.reset()

    def reset(self):
        """Reset the instance

        - reset rows and header
        """

        self._hline_string = None
        self._row_size = None
        self._header = []
        self._rows = []
        self._attr = {}

    def header(self, array):
        """Specify the header of the table
        """

        self._check_row_size(array)
        self._header = map(str, array)

    def add_row(self, array):
        """Add a row in the rows stack

        - cells can contain newlines and tabs
        """

        self._check_row_size(array)
        self._rows.append(map(str, array))

    def add_rows(self, rows, header=True):
        """Add several rows in the rows stack

        - The 'rows' argument can be either an iterator returning arrays,
          or a by-dimensional array
        - 'header' specifies if the first row should be used as the header
          of the table
        """

        # nb: don't use 'iter' on by-dimensional arrays, to get a
        #     usable code for python 2.1
        if header:
            if hasattr(rows, '__iter__') and hasattr(rows, 'next'):
                self.header(rows.next())
            else:
                self.header(rows[0])
                rows = rows[1:]
        for row in rows:
            self.add_row(row)

    def set_attr(self, attr, row = None, col = None ):
	"""Define clell colors (RGBCMY)
	- set_attr( 'R' )		- default to 'R' for all cells
	- set_attr( 'R', r )		- 'R' for all cells in row r
	- set_attr( 'R', None, c )	- 'R' for all cells in col c
	- set_attr( 'R', r, c )		- 'R' for cell (r,c)
	"""
	if not self._attr.has_key( row ):
	  self._attr[row] = {}
	self._attr[row][col] = attr


    def set_chars(self, array):
        """Set the characters used to draw lines between rows and columns

        - the array should contain 4 fields:

            [horizontal, vertical, corner, header]

        - default is set to:

            ['-', '|', '+', '=']
        """

        if len(array) != 4:
            raise ArraySizeError, "array should contain 4 characters"
        array = [ x[:1] for x in [ str(s) for s in array ] ]
        (self._char_horiz, self._char_vert,
            self._char_corner, self._char_header) = array

    def set_deco(self, deco):
        """Set the table decoration

        - 'deco' can be a combinaison of:

            Texttable.BORDER: Border around the table
            Texttable.HEADER: Horizontal line below the header
            Texttable.HLINES: Horizontal lines between rows
            Texttable.VLINES: Vertical lines between columns

           All of them are enabled by default

        - example:

            Texttable.BORDER | Texttable.HEADER
        """

        self._deco = deco

    def set_cols_align(self, array):
        """Set the desired columns alignment

        - the elements of the array should be either "l", "c" or "r":

            * "l": column flushed left
            * "c": column centered
            * "r": column flushed right
        """

        self._check_row_size(array)
        self._align = array

    def set_cols_valign(self, array):
        """Set the desired columns vertical alignment

        - the elements of the array should be either "t", "m" or "b":

            * "t": column aligned on the top of the cell
            * "m": column aligned on the middle of the cell
            * "b": column aligned on the bottom of the cell
        """

        self._check_row_size(array)
        self._valign = array

    def set_cols_width(self, array):
        """Set the desired columns width

        - the elements of the array should be integers, specifying the
          width of each column. For example:

                [10, 20, 5]
        """

        self._check_row_size(array)
        try:
            array = map(int, array)
            if reduce(min, array) <= 0:
                raise ValueError
        except ValueError:
            sys.stderr.write("Wrong argument in column width specification\n")
            raise
        self._width = array

    def draw(self):
        """Draw the table

        - the table is returned as a whole string
        """

        if not self._header and not self._rows:
            return
        self._compute_cols_width()
        self._check_align()
	self._draw_line_num = 0; # increment in _draw_line
        out = ""
        if self._has_border():
            out += self._hline()
        if self._header:
            out += self._draw_line(self._header, isheader=True)
            if self._has_header():
                out += self._hline_header()
        length = 0
        for row in self._rows:
            length += 1
            out += self._draw_line(row)
            if self._has_hlines() and length < len(self._rows):
                out += self._hline()
        if self._has_border():
            out += self._hline()
        return out[:-1]

    def _check_row_size(self, array):
        """Check that the specified array fits the previous rows size
        """

        if not self._row_size:
            self._row_size = len(array)
        elif self._row_size != len(array):
            raise ArraySizeError, "array should contain %d elements" \
                % self._row_size

    def _has_vlines(self):
        """Return a boolean, if vlines are required or not
        """

        return self._deco & Texttable.VLINES > 0

    def _has_hlines(self):
        """Return a boolean, if hlines are required or not
        """

        return self._deco & Texttable.HLINES > 0

    def _has_border(self):
        """Return a boolean, if border is required or not
        """

        return self._deco & Texttable.BORDER > 0

    def _has_header(self):
        """Return a boolean, if header line is required or not
        """

        return self._deco & Texttable.HEADER > 0

    def _hline_header(self):
        """Print header's horizontal line
        """

        return self._build_hline(True)

    def _hline(self):
        """Print an horizontal line
        """

        if not self._hline_string:
            self._hline_string = self._build_hline()
        return self._hline_string

    def _build_hline(self, is_header=False):
        """Return a string used to separated rows or separate header from
        rows
        """
        horiz = self._char_horiz
        if (is_header):
            horiz = self._char_header
        # compute cell separator
        s = "%s%s%s" % (horiz, [horiz, self._char_corner][self._has_vlines()],
            horiz)
        # build the line
        l = string.join([horiz*n for n in self._width], s)
        # add border if needed
        if self._has_border():
            l = "%s%s%s%s%s\n" % (self._char_corner, horiz, l, horiz,
                self._char_corner)
        else:
            l += "\n"
        return l

    def _len_cell(self, cell):
        """Return the width of the cell

        Special characters are taken into account to return the width of the
        cell, such like newlines and tabs
        """

        cell_lines = cell.split('\n')
        maxi = 0
        for line in cell_lines:
            length = 0
            parts = line.split('\t')
            for part, i in zip(parts, range(1, len(parts) + 1)):
                length = length + len(part)
                if i < len(parts):
                    length = (length/8 + 1)*8
            maxi = max(maxi, length)
        return maxi

    def _compute_cols_width(self):
        """Return an array with the width of each column

        If a specific width has been specified, exit. If the total of the
        columns width exceed the table desired width, another width will be
        computed to fit, and cells will be wrapped.
        """

        if hasattr(self, "_width"):
            return
        maxi = []
        if self._header:
            maxi = [ self._len_cell(x) for x in self._header ]
        for row in self._rows:
            for cell,i in zip(row, range(len(row))):
                try:
                    maxi[i] = max(maxi[i], self._len_cell(cell))
                except (TypeError, IndexError):
                    maxi.append(self._len_cell(cell))
        items = len(maxi)
        length = reduce(lambda x,y: x+y, maxi)
        if self._max_width and length + items*3 + 1 > self._max_width:
            maxi = [(self._max_width - items*3 -1) / items \
                for n in range(items)]
        self._width = maxi

    def _check_align(self):
        """Check if alignment has been specified, set default one if not
        """

        if not hasattr(self, "_align"):
            self._align = ["l"]*self._row_size
        if not hasattr(self, "_valign"):
            self._valign = ["t"]*self._row_size

    def colorize_text( self, attr, text ):
	if attr == None or not self._attr_val.has_key( attr ):
	  return text
	return "%s%s%s" % ( self._attr_val[attr], text,  self._attr_val[None] )

    def _set_cell_attr( self, row, col, text ):
	if len( self._attr ) == 0:
	  return text

	a = None
	if self._attr.has_key( row ):
	  r = self._attr[row]
	  if r.has_key( col ):
	    a = r[col]
	  elif r.has_key( None ):
	    a = r[None]

	if a == None and  self._attr.has_key( None ):
	  r = self._attr[None]
	  if r.has_key( col ):
	    a = r[col]
	  elif r.has_key( None ):
	    a = r[None]

	return self.colorize_text( a, text )

    def _draw_line(self, line, isheader=False):
        """Draw a line

        Loop over a single cell length, over all the cells
        """

        line = self._splitit(line, isheader)
        space = " "
        out  = ""
        for i in range(len(line[0])):
            if self._has_border():
                out += "%s " % self._char_vert
            length = 0
            for cell, width, align in zip(line, self._width, self._align):
                cell_line = cell[i]
                fill = width - len(cell_line)
		cell_line = self._set_cell_attr( self._draw_line_num, length, cell_line )
                if isheader:
                    align = "c"
                if align == "r":
                    out += "%s " % (fill * space + cell_line)
                elif align == "c":
                    out += "%s " % (fill/2 * space + cell_line \
                            + (fill/2 + fill%2) * space)
                else:
                    out += "%s " % (cell_line + fill * space)
                length += 1
                if length < len(line):
                    out += "%s " % [space, self._char_vert][self._has_vlines()]
            out += "%s\n" % ['', self._char_vert][self._has_border()]
	self._draw_line_num+=1
        return out

    def _splitit(self, line, isheader):
        """Split each element of line to fit the column width

        Each element is turned into a list, result of the wrapping of the
        string to the desired width
        """

        line_wrapped = []
        for cell, width in zip(line, self._width):
            array = []
            for c in cell.split('\n'):
                array.extend(textwrap.wrap(c, width))
            line_wrapped.append(array)
        max_cell_lines = reduce(max, map(len, line_wrapped))
        for cell, valign in zip(line_wrapped, self._valign):
            if isheader:
                valign = "t"
            if valign == "m":
                missing = max_cell_lines - len(cell)
                cell[:0] = [""] * (missing / 2)
                cell.extend([""] * (missing / 2 + missing % 2))
            elif valign == "b":
                cell[:0] = [""] * (max_cell_lines - len(cell))
            else:
                cell.extend([""] * (max_cell_lines - len(cell)))
        return line_wrapped

if __name__ == '__main__':
    table = Texttable()
    table.set_cols_align(["l", "r", "c"])
    table.set_cols_valign(["t", "m", "b"])
    table.add_rows([ ["Name", "Age", "Nickname"],
                     ["Mr\nXavier\nHuon", 32, "Xav'"],
                     ["Mr\nBaptiste\nClement", 1, "Baby"] ])
    print table.draw()
