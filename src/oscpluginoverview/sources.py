import string, sys
import urllib2
import os

# if (rpm.labelCompare((None, version, '1'), (None, bsver, '1')) == 1) :  

class PackageSource:
    """
    Represents one repository of packages, for example
    a OBS repo, a gem server, a upstream ftp.
    """
    pass

class BuildServiceSource(PackageSource):
    def __init__(self, service, project):
        self.service = service
        self.project = project
        

    def packages(self):
        import osc.core
        pkgs = osc.core.meta_get_packagelist(self.service, self.project)
        return pkgs
        pass
    
    def version(self, package):
        """
        Returns the version for a package
        Package must exist in packages()
        """
        try:
            from xml.etree import cElementTree as ET
        except ImportError:
            import cElementTree as ET

        import osc.core
        import osc.conf
        # There's got to be a more efficient way to do this :(
        u = osc.core.makeurl(self.service, ['source', self.project, package, '_history'])
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

class GemSource(PackageSource):
    """
    gem server
    """
    # cache gem server name -> package list
    _gemlist = {}

    def __init__(self, gemserver):
        self.gemserver = gemserver
        
    def packages(self):
        # if the list is not cached, cache it
        if not GemSource._gemlist.has_key(self.gemserver):
            try:
                if os.environ.has_key("OSC_RUBY_TEST"):
                    fd = open("/tmp/index")
                else:
                    fd = urllib2.urlopen("http://gems.rubyforge.org/quick/index")
                    import rpm
                    gems = {}
                    for line in fd:
                        name, version = line.strip().rsplit('-', 1)
                        gems["rubygem-%s" % name] = version
                    GemSource._gemlist[self.gemserver] = gems
            except urllib2.HTTPError, e:
                raise Exception('Cannot get upstream gem index')
            except IOError:
                raise Exception('Cannot get local index')
            except Exception as e:
                print e
                raise Exception("Unexpected error: {0}".format(sys.exc_info()[0]))
        # return the cache entry
        return GemSource._gemlist[self.gemserver].keys()
    
    def version(self, package):
        """
        Returns the version for a package
        Package must exist in packages()
        """
        # call packages just to make sure the cache is filled
        self.packages()
        return GemSource._gemlist[self.gemserver][package]

    
def createSourceFromUrl(url):
    try:
        kind, name = url.split('://')
    except ValueError:
        print "invalid origin format: %s" % repo
        
    if kind == "obs":
        api = 'https://api.opensuse.org'
        if name[0:5] == "SUSE:":
            api = "http://api.suse.de"

        return BuildServiceSource(api, name)
    elif kind == "gem":
        return GemSource(name)

    raise "Unsupported source type %s" % url
