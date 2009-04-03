
import string, sys

def _apiurl(self, project):
    if project[0:5] == "SUSE:" in project:
        return "http://api.suse.de"
    else:
        return "http://api.opensuse.org"

def _pacversion(self, project, package):
    """
    Returns the version of a package present in a project

    The API url is determined by the project name.
    
    """
    
    apiurl = self._apiurl(project)
    #print apiurl
    
    try:
        from xml.etree import cElementTree as ET
    except ImportError:
        import cElementTree as ET

    import osc.core
    import osc.conf
    # There's got to be a more efficient way to do this :(
    u = osc.core.makeurl(apiurl, ['source', project, package, '_history'])
    try:
        f = osc.core.http_GET(u)
    except urllib2.HTTPError, e:
        raise self.Error("Cannot get package info from: %s".format(u))
        
    root = ET.parse(f).getroot()

    r = []
    revisions = root.findall('revision')
    revisions.reverse()
    version = 0
    for node in revisions:
        version = node.find('version').text
        break

    return version

def _changes(self, group):
    #https://api.opensuse.org/source/zypp:Head/libzypp/libzypp.changes
    import ConfigParser
    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser("~/.osc-overview/%s.ini" % group ))

    import texttable
    #for view in config.sections():




class View:
    def __init__(self, group, name):
        self.group = group
        self.name = name
        import ConfigParser
        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.expanduser("~/.osc-overview/%s.ini" % name ))

    def repos(self):
        if config.has_option(view, 'repos'):
            repos = config.get(view,'repos').split(',')
            return repos
        return []

    def packages(self):
        if config.has_option(view, 'packages'):
            packages = config.get(view,'packages').split(',')
            return packages
        return []

class Group:
    def __init__(self, name):
        self.name = name
        import ConfigParser
        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.expanduser("~/.osc-overview/%s.ini" % name ))
    def config(self):
        return self.config
    def views(self):
        views = []
        #for i in self.config.sections():
        #    views.append(Gr
    


def _overview(self, group):
    import ConfigParser
    config = ConfigParser.ConfigParser()
    config.read(os.path.expanduser("~/.osc-overview/%s.ini" % group ))

    import texttable
    for view in config.sections():

        table = texttable.Texttable()
        rows = []
        packages = []
        repos = []
        
        if config.has_option(view, 'packages'):
            packages = config.get(view,'packages').split(',')
            if len(packages) == 0:
                print "No packages defined"
                break
            
        if config.has_option(view, 'repos'):
            repos = config.get(view,'repos').split(',')
            if len(repos) == 0:
                break

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
                    try:
                        kind, name = repo.split('://')
                    except ValueError:
                        print "invalid origin format: %s" % repo
                        
                    if kind == "obs":
                        version = self._pacversion(name, package)
                        row.append(version)
                    elif kind == "gem":
                        versions = self._ruby_gem_versions(name)
                        version = versions[package.replace('rubygem-', '')]
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

    #products = { "openSUSE 11.1" : { 'garepo': 'openSUSE:11.1', 'testrepo': '', 'updaterepo': 'openSUSE:11.1:Update', 'develrepo': 'devel:updatestack', pkgs = [ 'libzypp', 'zypper' ] } }    

def _ruby_gem_versions(self, gemserver):
    try:
        if os.environ.has_key("OSC_RUBY_TEST"):
            fd = open("/tmp/index")
        else:
            fd = urllib2.urlopen("http://gems.rubyforge.org/quick/index")
            
        import rpm
        gems = {}
        for line in fd:
            name, version = line.strip().rsplit('-', 1)
            gems[name] = version

        return gems
    
    except urllib2.HTTPError, e:
        raise Exception('Cannot get upstream gem index')
    except IOError:
        raise Exception('Cannot get local index')
    except Exception as e:
        print e
        raise Exception("Unexpected error: {0}".format(sys.exc_info()[0]))

                           
def _ruby_todo(self, apiurl, projects):
    bs_pkgs = []
    for project in projects:
        pkgs = meta_get_packagelist(conf.config['apiurl'], project)
        for pkg in pkgs:
            if ( pkg.find("rubygem-") != -1 ):
                if not pkg in bs_pkgs:
                    bs_pkgs.append(pkg)

    print("%d gems in build service projects" % len(bs_pkgs))
    #pkgs = self._paclist(projects[0])

    import osc.core

    # get the gem index
    
    print("Retrieving upstream gem information...")
    try:
        if os.environ.has_key("OSC_RUBY_TEST"):
            fd = open("/tmp/index")
        else:
            fd = urllib2.urlopen("http://gems.rubyforge.org/quick/index")

        ups_versions = {}
        
        import rpm

        for line in fd:
            name, version = line.strip().rsplit('-', 1)
            gempkg = "rubygem-" + name
            # only take it into account if the gem is also in the build
            # service
            if bs_pkgs.count(gempkg) > 0 :
                # the gem is also in the build service, lets compare versions
                # if we already saw this gem, check that this version in
                # obs is newer before
                if ups_versions.has_key(name):
                    newer = ups_versions.get(name)
                    # check if the version we found is newer
                    compare = rpm.labelCompare((None, version, '1'), (None, newer, '1'))
                    #print "{0} {1} {2}".format(version, newer, compare)
                    if ( compare == 1 ) :
                        ups_versions[name ] = version
                else:
                    ups_versions[name ] = version
            
        # now ups_versions contains the newer gem per gem name
        # now check if some gems are newer
        for (name, version) in ups_versions.items():
            gempkg = "rubygem-" + name
            if gempkg in bs_pkgs:
                try:
                    bsver = self._pacversion(projects[0], gempkg)
                except:
                    error = "Cannot retrieve version for {0}".format(name)
                    print error
                    raise Exception(error)
                else:
                    if ( bsver == "0" ):
                        print("ERROR: {0} may have no source uploaded".format(name))
                        continue
                    if (rpm.labelCompare((None, version, '1'), (None, bsver, '1')) == 1) :
                        print("+ {0} upstream: {1} bs: {2}".format(name, version, bsver))
                    #else:
                    #    print("- {0} upstream: {1} bs: {2}".format(name, version, bsver))
    except urllib2.HTTPError, e:
        raise Exception('Cannot get upstream gem index')
    except IOError:
        raise Exception('Cannot get local index')
    except Exception as e:
        print e
        raise Exception("Unexpected error: {0}".format(sys.exc_info()[0]))
    
def do_overview(self, subcmd, opts, *args):

    sys.path.append(os.path.expanduser('~/.osc-plugins'))
    
    pyverstr = sys.version.split()[0]
    pyver = pyverstr.split(".")
    if map(int, pyver) < [2, 6]:
        error = "Sorry, osc ruby requires Python 2.6, you have {0}".format(pyverstr)
        print(error)
        exit(1)
    
    """${cmd_name}: Various commands to ease software management maintenance.

    "todo" (or "t") will list the packages that need some action.

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
    
    self._overview(cmd)

