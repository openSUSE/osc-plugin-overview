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

    # cache for package list
    # service/project -> list
    _packagelist = {}
    
    def __init__(self, service, project):
        self.service = service
        self.project = project
        
    def packages(self):
        key = self.service + "/" + self.project
        if not BuildServiceSource._packagelist.has_key(key):      
            import osc.core
            BuildServiceSource._packagelist[key] = osc.core.meta_get_packagelist(self.service, self.project)
        return BuildServiceSource._packagelist[key]
    
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
            print "Cannot get package info from: %s" % u
            exit(1)
        
        root = ET.parse(f).getroot()
        
        r = []
        revisions = root.findall('revision')
        revisions.reverse()
        version = 0
        for node in revisions:
            version = node.find('version').text
            break
        
        return version

#get_submit_request_list(apiurl, project, package, req_state=('new')):

class BuildServicePendingRequestsSource(PackageSource):
    # cache service/repo -> list
    _packagelist = {}
    _srlist = {}
    
    def __init__(self, service, project):
        self.service = service
        self.project = project

    def packages(self):
        key = self.service + "/" + self.project
        if not BuildServicePendingRequestsSource._packagelist.has_key(key):
            BuildServicePendingRequestsSource._packagelist[key] = []
            BuildServicePendingRequestsSource._srlist[key] = []
            import osc.core
            # we use empty package to get all
            requests =  osc.core.get_submit_request_list(self.service, self.project, '', req_state=('new'))
            for req in requests:
                BuildServicePendingRequestsSource._srlist[key].append(req)
                # cache the packages only too
                BuildServicePendingRequestsSource._packagelist[key].append(req.src_package)
                
        return BuildServicePendingRequestsSource._packagelist[key]
        
    def version(self, package):
        try:
            from xml.etree import cElementTree as ET
        except ImportError:
            import cElementTree as ET

        import osc.core
        #import osc.conf
        # just to make sure the info gets cached
        self.packages()
        for req in BuildServicePendingRequestsSource._srlist:
            if req.src_package == package:
                # now look for the revision in the history to figure out the version
                u = osc.core.makeurl(self.service, ['source', req.src_project, package, '_history'])
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
                    md5 = node.find('srcmd5').text
                    print md5
                    print req.src_md5

                    if md5 == req.src_md5:
                        version = node.find('version').text
                        return version
        return None
    


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
            except Exception:
                #print e
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
        print "invalid origin format: %s" % url
        exit(1)
        
    if kind == "obs" or kind == "ibs" or kind == "ibssr" or kind == "obssr":
        # TODO automatically use internal if ibs or ibssr
        api = 'https://api.opensuse.org'
        if name[0:5] == "SUSE:":
            api = "http://api.suse.de"

        if kind == "obs" or kind == "ibs":
            return BuildServiceSource(api, name)
        elif kind == "obssr" or kind == "ibssr":
            return BuildServicePendingRequestsSource(api, name)
    elif kind == "gem":
        return GemSource(name)
    
    raise "Unsupported source type %s" % url
