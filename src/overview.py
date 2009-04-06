#
# Author: Duncan Mac-Vicar P. <dmacvicar@suse.de>
# Copyright (C) 2009 Novell Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

import string, sys
#from oscpluginoverview import texttable

def _changes(self, group):
    #https://api.opensuse.org/source/zypp:Head/libzypp/libzypp.changes
    import ConfigParser
    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser("~/.osc-overview/%s.ini" % group ))

    #for view in config.sections():

def _overview(self, group):
    import ConfigParser
    config = ConfigParser.ConfigParser()
        
    config.read(os.path.expanduser("~/.osc-overview/%s.ini" % group ))

    from oscpluginoverview.texttable import Texttable
    for view in config.sections():

        table = Texttable()
        rows = []
        packages = []
        repos = []
                    
        if config.has_option(view, 'repos'):
            repos = config.get(view,'repos').split(',')
            if len(repos) == 0:
                break

            data = {}
            for repo in repos:
                import oscpluginoverview.sources
                data[repo] = oscpluginoverview.sources.createSourceFromUrl(repo)

            if config.has_option(view, 'packages'):
                pkgopt = config.get(view,'packages')
                packages = oscpluginoverview.sources.evalPackages(repos, data, pkgopt)
            header = []
            #header.append(" ")
            header.append("package")
            for r in repos:
                header.append(r)
                
            rows.append(header)
            
            for package in packages:
                row = []
                # append the package name, then we add the versions
                row.append(package)

                # now we see this package in various repos
                changes = []
                
                for repo in repos:
                    if package  in data[repo].packages():
                        version = data[repo].version(package)
                        row.append(version)
                    else:
                        row.append("-")
                # append the resulting row to the table
                rows.append(row)
            # append all rows to the table
            table.add_rows(rows)
            print "** %s ** " % view
            print table.draw()
            print
            
        else:
            print "No repos defined for %s" % view
            continue

def do_overview(self, subcmd, opts, *args):

    if not os.path.exists(os.path.expanduser("~/.osc-overview")):
        print "Drop your views in ~/.osc-overview"
        exit(1)

    sys.path.append(os.path.expanduser('~/.osc-plugins'))
    
    #pyverstr = sys.version.split()[0]
    #pyver = pyverstr.split(".")
    #if map(int, pyver) < [2, 6]:
    #    error = "Sorry, osc ruby requires Python 2.6, you have {0}".format(pyverstr)
    #    print(error)
    #    exit(1)
    
    """${cmd_name}: Various commands to ease maintenance.

    "overview" (or "o") will list the packages that need some action.

    Usage:
        osc overview group

        You should define your groups in ~/.osc-overview/$group.ini
        
    """

    cmds = []
    cfgfiles = os.listdir(os.path.expanduser('~/.osc-overview'))
    for cfg in cfgfiles:
        cmds.append(os.path.basename(cfg.replace('.ini','')))
    
    if not args or not os.path.exists(os.path.expanduser('~/.osc-overview/%s.ini' % args[0]) ):
        raise oscerr.WrongArgs('Unknown action. Choose one of: %s.' \
                                           % ', '.join(cmds))
    cmd = args[0]

    min_args, max_args = 0, 0

    if len(args) - 1 < min_args:
        raise oscerr.WrongArgs('Too few arguments.')
    if len(args) - 1 > max_args:
        raise oscerr.WrongArgs('Too many arguments.')

    from oscpluginoverview.sources import GemSource, BuildServiceSource, BuildServicePendingRequestsSource
    
    #gems = GemSource("foo")
    #print gems.packages()
    #print gems.version('rubygem-hpricot')
    #obs = BuildServiceSource('http://api.opensuse.org', 'zypp:Head')
    #print obs.packages()
    #print obs.version('libzypp')

    #reqs = BuildServicePendingRequestsSource('http://api.opensuse.org', 'openSUSE:Factory')
    #print reqs.packages()
    #print reqs.version("patch")

    self._overview(cmd)

