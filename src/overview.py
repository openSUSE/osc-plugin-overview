#
# Author: Duncan Mac-Vicar P. <dmacvicar@suse.de>
# Copyright (C) 2009 Novell Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
from osc import cmdln
from osc import oscerr

def _changes(self, group):
    #https://api.opensuse.org/source/zypp:Head/libzypp/libzypp.changes
    import ConfigParser
    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser("~/.osc-overview/%s.ini" % group ))

    #for view in config.sections():

def _overview(self, group, opts):
    import ConfigParser
    import oscpluginoverview.sources

    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser("~/.osc-overview/%s.ini" % group ))

    for secname in config.sections():
        if ( opts.color ):
            config.set( secname, 'color', 'True' )
        if ( opts.no_color ):
            config.set( secname, 'color', 'False' )

        view = oscpluginoverview.sources.View(secname, config)
        view.readConfig()

        view.printTable()
        if opts.changelog or view.showChanges == "1":
            view.printChangelog()
        if opts.patchinfo:
            view.printPatchinfo()


@cmdln.option('-c', '--changelog', action='store_true',
              help='Also output repo changelog')
@cmdln.option('-p', '--patchinfo', action='store_true',
              help='Also output repo patchinfo file')
@cmdln.option('', '--color', action='store_true',
              help='Colorize the output')
@cmdln.option('', '--no-color', action='store_true',
              help='Don not colorize the output')


def do_overview(self, subcmd, opts, *args):
    """${cmd_name}: Overview of various repositories.

    For a full description, read:
    http://en.opensuse.org/openSUSE:OSC_overview_plugin

    overview viewname : will attempt to read the group from
    ~/.osc-overview/groupname.ini and display the data.

    Options:
      -c, --changelog
           display diff of changes across the newest and the previous
           versions of the packages.
      -p, --patchinfo
           Create a patchinfo template
      --color
           Colorize the output. Also 'color=1' in $group.ini.
      --no-color
           Do not colorize the output. Also 'color=0' in $group.ini.

    Usage:
      osc overview [Options] {group}

      You should define your groups in ~/.osc-overview/$group.ini

    """
    if not os.path.exists(os.path.expanduser("~/.osc-overview")):
        print("Drop your views in ~/.osc-overview")
        exit(1)

    sys.path.append(os.path.expanduser('~/.osc-plugins'))

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
    #print(gems.packages())
    #print(gems.version('rubygem-hpricot'))
    #obs = BuildServiceSource('http://api.opensuse.org', 'zypp:Head')
    #print(obs.changelog('libzypp'))
    #print(obs.packages())
    #print(obs.version('libzypp'))

    #reqs = BuildServicePendingRequestsSource('http://api.opensuse.org', 'openSUSE:Factory')
    #print(reqs.packages())
    #print(reqs.version("patch"))

    self._overview(cmd, opts)


