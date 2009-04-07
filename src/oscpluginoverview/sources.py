import string, sys
import urllib2
import os

# if (rpm.labelCompare((None, version, '1'), (None, bsver, '1')) == 1) :  

def evalRepo(repos, expr):
    """
    evaluates a repo from a $x expression
    """    
    import re
    repo = None
    matches = re.findall('\$(\d+)', expr)
    if len(matches) > 0:
        from string import atoi
        column = atoi(matches[0])
        if len(repos) < column:
            print "Can't use repo #%d package list, not enough repos" % column
            exit(1)
        repo = repos[column-1]
    else:
        # if not a expression evaluate it as a string
        if expr in repos:
            return expr
    return repo

def evalPackages(repos, data, pkgopt):
    repo = evalRepo(repos, pkgopt)
    packages = []
    if repo == None:
        # if no column specified, a package list
        # must be splited
        packages = pkgopt.split(',')
    else:
        packages = data[repo].packages()
    if len(packages) == 0:
        print "No packages defined for $s" % view
        exit(1)
    return packages

class PackageSource:
    """
    Represents one repository of packages, for example
    a OBS repo, a gem server, a upstream ftp.
    """
    pass

class CachedSource(PackageSource):
    """
    Wrapper that provides cache services to
    an existing source
    """
    
    def __init__(self, source):
        self.source = source
        self.pkglist = None
        self.versions = {}

    def packages(self):
        if self.pkglist == None:
            self.pkglist = self.source.packages()
        return self.pkglist
    def version(self, package):
        if not self.versions.has_key(package):
            self.versions[package] = self.source.version(package)
        return self.versions[package]

class BuildServiceSource(PackageSource):

    def __init__(self, service, project):
        self.service = service
        self.project = project
        
    def packages(self):
        import osc.core
        return  osc.core.meta_get_packagelist(self.service, self.project)
    
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
            srlist = BuildServicePendingRequestsSource._srlist[key]
            pkglist = BuildServicePendingRequestsSource._packagelist[key]
            for req in requests:
                srlist.append(req)
                # cache the packages only too
                pkglist.append(req.src_package)
        
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
        key = self.service + "/" + self.project
        for req in BuildServicePendingRequestsSource._srlist[key]:
            if req.src_package == package:
                # now look for the revision in the history to figure out the version
                u = osc.core.makeurl(self.service, ['source', req.src_project, package, '_history'])
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
                    md5 = node.find('srcmd5').text
                    #print md5
                    #print req.src_md5

                    if md5 == req.src_md5:
                        print "found %s" % u
                        version = node.find('version').text
                        return version
        return None
    


class GemSource(PackageSource):
    """
    gem server
    """
    # cache gem server name -> package list

    def __init__(self, gemserver):
        self.gemserver = gemserver
        # map gemname to version
        self.gems = None

    def readGemsOnce(self):
        if self.gems == None:
            try:
                self.gems = {}
                if os.environ.has_key("OSC_RUBY_TEST"):
                    fd = open("/tmp/index")
                else:
                    fd = urllib2.urlopen("http://%s/quick/index" % self.gemserver)
                    import rpm
                    gems = {}
                    for line in fd:
                        name, version = line.strip().rsplit('-', 1)
                        self.gems["rubygem-%s" % name] = version
            except urllib2.HTTPError, e:
                raise Exception('Cannot get upstream gem index')
            except IOError:
                raise Exception('Cannot get local index')
            except Exception:
            #print e
                raise Exception("Unexpected error: %s" % sys.exc_info()[0])
        
    def packages(self):
        # return the cache entry
        self.readGemsOnce()
        return self.gems.keys()
    
    def version(self, package):
        """
        Returns the version for a package
        Package must exist in packages()
        """
        # call packages just to make sure the cache is filled
        self.readGemsOnce()
        return self.gems[package]


class FreshmeatSource(PackageSource):
    """
    freshmeat.net project description
    """
    def __init__(self):
        pass
    def _keynat(self, string):
        r = []
        for c in string:
            try:
                c = int(c)
                try: r[-1] = r[-1] * 10 + c
                except: r.append(c)
            except:
                r.append(c)
        return r

    def _fetch(self, package):
        versions = []
        try:
            fd = urllib2.urlopen("http://freshmeat.net/projects/%s/releases" % package)
            html = "\n".join(fd.readlines())
            fd.close()
            from BeautifulSoup import BeautifulSoup
            soup = BeautifulSoup(html)
            for li in soup.findAll('li', attrs={'class': 'release'}):
                a = li.findNext('a')
                version = a.string
                versions.append(version)
                pass
        except urllib2.HTTPError, e:
            raise Exception('Cannot retrieve project information from freshmeat.net for %s' % package)
        except Exception:
            raise Exception('Unexpected error while fetching project information from fresheat.net for %s: %s' % (package, sys.exc_info()[0]))

        if len(a) < 1:
            return None
        return sorted(versions, key=self._keynat)[-1]
        #return versions

    def packages(self):
        raise Exception("querying package list from freshmeat not supported. Use a different source as the base package list or specify the package list manually")
    def version(self, package):
        return self._fetch(package)
    pass

    
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
            return CachedSource(BuildServiceSource(api, name))
        elif kind == "obssr" or kind == "ibssr":
            return BuildServicePendingRequestsSource(api, name)
    elif kind == "gem":
        return CachedSource(GemSource(name))
    elif kind == "fm":
        try:
            from BeautifulSoup import BeautifulSoup
        except ImportError:
            raise "Unsupported source type %s: you must install the package python-beautifulsoup first" % kind
        return CachedSource(FreshmeatSource())

    
    raise "Unsupported source type %s" % url
