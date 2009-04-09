import string, sys
import urllib2
import os
import rpm

# if (rpm.labelCompare((None, version, '1'), (None, bsver, '1')) == 1) :  

class View:
    """
    Represents a view of various packages across various sources
    """
    def __init__(self, name, config):
        self.name = name
        # map repo-name -> map packages -> versions
        self.versions = {}
        # reverse index
        # map package -> map repos -> versions
        self.versions_rev = {}
        self.config = config
        self.packages = []
        self.repos = []
        # data sources objects, per repo
        self.data = {}
        # filter list, for each package row tells where the package
        # is hidden by filters
        self.filter = []
        pass

    def setVersionForPackage(self, repo, package, version):
        """
        Sets the known version of a package in a repo
        """
        if not self.versions.has_key(repo):
            self.versions[repo] = {}
        if not self.versions_rev.has_key(package):
            self.versions_rev[package] = {}

        self.versions[repo][package] = version
        self.versions_rev[package][repo] = version

    def printTable(self):
        #print ",".join(self.filter)
        from oscpluginoverview.texttable import Texttable
        table = Texttable()
        rows = []

        header = []
        #header.append(" ")
        header.append("package")
        for r in self.repos:
            header.append(r)

        rows.append(header)

        for p in self.packages:
            # Don't print if the package is filtered
            if p in self.filter:
                continue
            row = []
            row.append(p)
            for r in self.repos:
                v = self.versions[r][p]
                if v == None:
                    row.append('-')
                else:
                    row.append(v)
            rows.append(row)
            
        #versions[repo] = version
        #row.append(version)
        #packages = oscpluginoverview.sources.evalPackages(repos, data, pkgopt)
        table.add_rows(rows)
        print "** %s ** " % self.name
        print table.draw()
        print

    def printChangelog(self):
        # find higher version per package and where does it come from
        # map package to bigger version
        skippedlines = []
        for package, repovers in self.versions_rev.items():
            res = sorted(repovers.items(), lambda x,y: rpm.labelCompare((None, str(x[1]), '1'), (None, str(y[1]), '1')) )

            # now we have a list of tuples (repo, version) for this package
            # we find the last two and ask for the changes file
            if len(res) >= 2:
                # check that the bigger is not none
                if res[len(res)-1][1]:
                    if res[len(res)-2][1]:
                        # ok we can do a diff
                        reponew = res[len(res)-1][0]
                        repoold = res[len(res)-2][0]
                        print "------- %s ( %s vs %s )" % (package, reponew, repoold)
                        changesnew = self.data[reponew].changelog(package)
                        changesold = self.data[repoold].changelog(package)
                        import difflib
#                        diff = difflib.unified_diff(changesold.splitlines(1), changesnew.splitlines(1), charjunk=lambda c:c in " \t\n")
                        differ = difflib.Differ(charjunk=lambda x: x in " \t\x0a", linejunk=lambda x: x in " \t\0x0a")
                        linesold = changesold.splitlines(1)
                        linesold = map(lambda x: string.strip(x, " "), linesold)
                        linesnew = changesnew.splitlines(1)
                        linesnew = map(lambda x: string.strip(x, " "), linesnew)

                        diff = differ.compare(linesold, linesnew)
                        lastline = None
                        difflines = []
                        skip = False
                        for line in diff:
                            if line[0] == '+' or line[0] == '-' or line[0] == '?':
                                sys.stdout.write(line)
                            continue
                            
                            if not lastline:
                                lastline = line
                                continue

                            s = difflib.SequenceMatcher(lambda x: x in " \t+-", lastline, line )
                            if s.ratio() > 0.9:
                                print s.ratio()
                                print "Found MATCH %f" % s.ratio()
                                print "** %s" % lastline
                                print "** %s" % line
                                for tag, i1, i2, j1, j2 in s.get_opcodes():
                                    print ("%7s a[%d:%d] (%s) b[%d:%d] (%s)" % (tag, i1, i2, lastline[i1:i2], j1, j2, line[j1:j2]))

                                lastline = None
                                continue
                            else:
                                sys.stdout.write(lastline)
                                lastline = line

                        #difflines.append(line)
                else:
                    # if it is none, continue
                    continue
                
            else:
                pass
    
    def readConfig(self):
        config = self.config
        view = self.name
        
        if config.has_option(view, 'repos'):
            self.repos = config.get(view,'repos').split(',')
            if len(self.repos) == 0:
                return
            
            for repo in self.repos:
                # resolve the repo uri to a data source object
                import oscpluginoverview.sources
                self.data[repo] = oscpluginoverview.sources.createSourceFromUrl(repo)

            if config.has_option(view, 'packages'):
                # resolve the packages list or macro
                pkgopt = config.get(view,'packages')
                self.packages = oscpluginoverview.sources.evalPackages(self.repos, self.data, pkgopt)
            
            for package in self.packages:
                row = []
                # append the package name, then we add the versions
                row.append(package)

                # now we see this package in various repos
                changes = []

                # save versions in a map repo -> version, to use in filters
                for repo in self.repos:
                    # initialize
                    if not self.versions.has_key(repo):
                        self.versions[repo] = {}
                    # the source may not support getting the package list
                    # in this case we just assume the package will be there
                    packageExists = False
                    try:
                        repopkgs = self.data[repo].packages()
                        if package in repopkgs:
                            packageExists = True
                    except:
                        packageExists = True
                        
                    if packageExists:
                        version = self.data[repo].version(package)
                    else:
                        version = None
                    self.setVersionForPackage(repo, package, version)

                # older filter, show the row _only_ if specified repo is
                # older than any other column
                showrow = True
                if config.has_option(view, 'filter.older'):
                    oldfilterrepo = oscpluginoverview.sources.evalRepo(self.repos, config.get(view,'filter.older'))
                    if oldfilterrepo == None:
                        print "Unknown repo %s as older filter" % oldfilterrepo
                        exit(1)
                    else:
                        showrow = False
                        baseversion = self.versions[oldfilterrepo][package]
                        import rpm
                        for cmprepo, cmpvers in self.versions.items():
                            # version to compare to
                            if not cmpvers.has_key(package):
                                continue
                            v = cmpvers[package]
                            # if the version is not there skip this row
                            if v == None:
                                continue
                            # see if any of the other versions is newer, and if
                            # yes, enable the row
                            if (rpm.labelCompare((None, str(v), '1'), (None, str(baseversion), '1')) == 1) and cmprepo != oldfilterrepo:
                                showrow = True
                
                # append to the filter if it should not be shown
                if not showrow:
                    self.filter.append(package)            
        else:
            print "No repos defined for %s" % view
            return

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
    def changelog(self, package):
        raise Exception("querying changelog from %s not supported. Use a different source" % self.label)

    def packages(self):
        raise Exception("querying package list from %s not supported. Use a different source as the base package list or specify the package list manually" % self.label)

    def version(self, package):
        raise Exception("querying package version from %s not supported. Use a different source" % self.label)

    def label(self):
        """
        description for messages
        """
        raise Exception("label not implemented")

class CachedSource(PackageSource):
    """
    Wrapper that provides cache services to
    an existing source
    """
    
    def __init__(self, source):
        self.source = source
        self.pkglist = None
        self.versions = {}
        self.changelogs = {}

    def changelog(self, package):
        if not self.changelogs.has_key(package):
            self.changelogs[package] = self.source.changelog(package)
        return self.changelogs[package]

    def packages(self):
        if self.pkglist == None:
            self.pkglist = self.source.packages()
        return self.pkglist
    def version(self, package):
        if not self.versions.has_key(package):
            self.versions[package] = self.source.version(package)
        return self.versions[package]

    def label(self):
        return self.source.label

class BuildServiceSource(PackageSource):

    def __init__(self, service, project):
        self.service = service
        self.project = project

    def label(self):
        return self.service + "/" + self.project

    def changelog(self, package):
        """
        Returns the changelog of a package
        in this case package.changes file
        """
        import osc.core
        import osc.conf
        # There's got to be a more efficient way to do this :(
        u = osc.core.makeurl(self.service, ['source', self.project, package, "%s.changes" % package])
        try:
            f = osc.core.http_GET(u)
        except urllib2.HTTPError, e:
            print "Cannot get package changelog from: %s" % u
            exit(1)        
        return f.read()
    
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
    """
    This class simulates a source with the submit requests
    against a build service project
    So you can see what is pending.
    """
    
    # cache service/repo -> list
    _packagelist = {}
    _srlist = {}

    def label(self):
        return "submit requests"
    
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

    def label(self):
        return "gems"

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

    def label(self):
        return "freshmeat"
    
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
