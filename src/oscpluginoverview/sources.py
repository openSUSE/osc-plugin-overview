import string, sys
import urllib2
import os
import rpm
import oscpluginoverview.diff
from cStringIO import StringIO
import osc.core
try:
    from xml.etree import cElementTree as ET
except ImportError:
    import cElementTree as ET

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
        # packages included in the changelog
        self.changelog_packages = []
        self.repos = []
        # data sources objects, per repo
        self.data = {}
        # filter list, for each package row tells where the package
        # is hidden by filters
        self.filter = []
        # the changelog of the whole view
        self.changelog = None
        # changes= option from ini file
        self.showChanges = 0
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
	table.set_attr( 'G', 0 )
	table.set_attr( 'B', None, 0 )
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
	    cmp = None
            for r in self.repos:
                v = self.versions[r][p]
                if v == None:
		    v = '-'
		if cmp == None:
		    cmp = v
		else:
		    if not v.startswith( cmp ):
		      table.set_attr( 'R', len(rows), len(row) )
		row.append(v)
            rows.append(row)

        #versions[repo] = version
        #row.append(version)
        #packages = oscpluginoverview.sources.evalPackages(repos, data, pkgopt)
        table.add_rows(rows)
        print "** %s ** " % self.name
        print table.draw()
        print

    def packageCompare(self, package, x, y):
        """
        Compares two packages based on version
        If the versions are the same, tries to get the mtime of the
        changes file

        receives two tuples (repo, version) as input
        """
        res = rpm.labelCompare((None, str(x[1]), '1'), (None, str(y[1]), '1'))
        # only fetch mtimes if the package is in the repo
        if res == 0 and x[1] and y[1]:
            return cmp(self.data[x[0]].mtime(package), self.data[y[0]].mtime(package))
        else:
            return res

    def changelogDiff(self):
        """
        Returns a diff with package changes
        (obtained from the .changes file) of the whole
        group. The 2 newer versions are used to compare
        """

        if not self.changelog:
            file_str = StringIO()
            file_str.write("Looking for changes..\n")

            # find higher version per package and where does it come from
            # map package to bigger version
            for package, repovers in self.versions_rev.items():
                res = sorted(repovers.items(), lambda x,y: self.packageCompare(package,x,y) )

                # now we have a list of tuples (repo, version) for this package
                # we find the last two and ask for the changes file. Take care
                # the package version is not None, and also the changelog isn't.
                # Changelog None indicates the repo does not provide changes (obssr://).
                if len(res) >= 2:
                    idx = len(res)-1
                    changesnew = None
                    reponew = None
                    while idx >= 0:
                        if res[idx][1]:
                            reponew = res[idx][0]
                            changesnew = self.data[reponew].changelog(package)
                        idx -= 1
                        if changesnew != None:
                            break
                    if changesnew == None:
                        continue

                    changesold = None
                    repoold = None
                    while idx >= 0:
                        if res[idx][1]:
                            repoold = res[idx][0]
                            changesold = self.data[repoold].changelog(package)
                        idx -= 1
                        if changesold != None:
                            break
                    if changesold == None:
                        continue

                    self.changelog_packages.append(package)
                    changesdiff = oscpluginoverview.diff.diff_strings(changesold, changesnew)
                    if not changesdiff:
                        # suppress empty diffs
                        continue

                    file_str.write("+--------------------------------------------------------------------------+\n")
                    file_str.write("------- %s ( %s vs %s )\n" % (package, reponew, repoold))
                    file_str.write("+--------------------------------------------------------------------------+\n")
                    file_str.write(changesdiff)
                    file_str.write("\n")

            self.changelog = file_str.getvalue()
        # if the changelog was cached
        # just return it
        return self.changelog

    def printChangelog(self):
        print self.changelogDiff()
        pass

    def printPatchinfo(self):
        import oscpluginoverview.patchinfo
        print oscpluginoverview.patchinfo.patchinfo_from_changelog(self.changelogDiff(), self.repos, self.changelog_packages)

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

            if config.has_option(view, 'changes'):
                self.showChanges = config.get(view,'changes')
            if config.has_option(view, 'packages'):
                # resolve the packages list or macro
                pkgopt = config.get(view,'packages')
                self.packages = oscpluginoverview.sources.evalMacro(self.repos, self.data, pkgopt)
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
                    oldfilterrepos = oscpluginoverview.sources.evalMacro(self.repos, self.data, config.get(view,'filter.older'))
                    if len(oldfilterrepos) != 1:
                        print "Only one source can be used as base for old filter"
                        exit(1)
                    else:
                        oldfilterrepo = oldfilterrepos[0]
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

def evalMacro(repos, data, expr):
    """
    evaluates a expression
    returns expanded version

    macros:
    $x repository in position x
    *x package list of repos in position x

    returns an ordered list of strings
    """
    import re
    ret = []
    components = expr.split(',')
    for component in components:
        matches = re.findall('\$(\d+)', component)
        if len(matches) > 0:
            from string import atoi
            column = atoi(matches[0])
            if len(repos) < column:
                print "Can't use repo #%d, not enough repos" % column
                exit(1)
            repo = repos[column-1]
            ret.append(repo)
        matches = re.findall('\*(\d+)', component)
        if len(matches) > 0:
            from string import atoi
            column = atoi(matches[0])
            if len(repos) < column:
                print "Can't use repo #%d package list, not enough repos" % column
                exit(1)
            repo = repos[column-1]
            packages = data[repo].packages()
            if len(packages) == 0:
                print "No packages defined for $s" % view
                exit(1)
            ret.extend(packages)
        else:
            # assume it is a repo
            ret.append(component)
    return ret

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

    def mtime(self, package):
	raise Exception("querying package mtime from %s not supported. Use a different source" % self.label)

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
        self.mtimes = {}

    def changelog(self, package):
        if not self.changelogs.has_key(package):
            self.changelogs[package] = self.source.changelog(package)
        return self.changelogs[package]

    def mtime(self, package):
        if not self.mtimes.has_key(package):
            self.mtimes[package] = self.source.mtime(package)
        return self.mtimes[package]

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

    def get_project_source_file(self, project, package, file, revision=None):
        """
        Returns the content of a source file
        and expand links if necessary

        if the file is not found, we fallback looking if the
        file is a linked package
        """
        import osc.core
        import osc.conf
        # There's got to be a more efficient way to do this :(

        query = None
        if revision:
            query = { 'rev': revision }
        # workaround
        u = None
        if query:
            u = osc.core.makeurl(self.service, ['source', project, package, file], query=query)
        else:
            u = osc.core.makeurl(self.service, ['source', project, package, file])

        try:
            f = osc.core.http_GET(u)
            return f.read()
        except urllib2.HTTPError, e:
            # ok may be it is a source link and this utterly sucks
            # but lets add some AI
            try:
                li = self.link_info(self.service, self.project, package)
                content = self.get_project_source_file(li.project, li.package, file, li.xsrcmd5)
                return content
            except urllib2.HTTPError, e:
                 # now really give up
                 print "Cannot get source file from: %s" % u
                 exit(1)

    def get_source_file(self, package, file, rev=None):
        return self.get_project_source_file(self.project, package, file, rev)

    def changelog(self, package):
        """
        Returns the changelog of a package
        in this case package.changes file
        """
        return self.get_source_file(package, "%s.changes" % package)

    def mtime(self, package):
        m = osc.core.show_files_meta(self.service, self.project, package)
        mtime = 0
        try:
            # only source link packages have a <linkinfo> element.
            entries = ET.parse(StringIO(''.join(m))).getroot().findall('entry')
            for entry in entries:
                entrytime = string.atoi(entry.get('mtime'))
                if entrytime > mtime:
                    mtime = entrytime
        except:
            return 0
        return mtime

    def packages(self):
        import osc.core
        return  osc.core.meta_get_packagelist(self.service, self.project)

    def parse_version(self, history):
        """
        Returns the version for a package
        Package must exist in packages()
        """
        f = StringIO(history)
        root = ET.parse(f).getroot()
        r = []
        revisions = root.findall('revision')
        revisions.reverse()
        version = 0
        for node in revisions:
            version = "%s\nrev %s" % (node.find('version').text, node.get('rev'))
            break

        return version

    def link_info(self, apiurl, prj, pac):
        m = osc.core.show_files_meta(apiurl, prj, pac)
        try:
            # only source link packages have a <linkinfo> element.
            li_node = ET.parse(StringIO(''.join(m))).getroot().find('linkinfo')
        except:
            return None

        li = osc.core.Linkinfo()
        li.read(li_node)

        if li.haserror():
            return None
            #raise oscerr.LinkExpandError, li.error
        else:
            return li

    def version(self, package):
        """
        Returns the version for a package
        Package must exist in packages()
        """
        history = self.get_project_source_file(self.project, package, "_history")
        version = self.parse_version(history)
        if version == "unknown":
            # may be it is a link
            li = self.link_info(self.service, self.project, package)
            if not li or not li.islink():
                return None
            # ma@:
            # According to mls@ the li.xsrcmd5 is not the right checksum. He
            # suggests to get the complete history, and get the version of entry
            # li.rev. Unfortunately osc.core.Linkinfo does not provide it ;(
            #
            # Appart from that, osc should be able to publish the version that is actually
            # used for building. Then we could stop all this link evaluation here.
            #
            # Disable the li.xsrcmd5 argument because this does not check the link, but
            # fails if the source and target package names differ, like in:
            #  obs://openSUSE:11.0:Update/yast2-pkg-bindings -> yast2-pkg-bindings-devel-doc
            #
            history = self.get_project_source_file(li.project, li.package, "_history") # , li.xsrcmd5)
            return self.parse_version(history)
        return version

class BuildServicePendingRequestsSource(PackageSource):
    """
    This class simulates a source with the submit requests
    against a build service project
    So you can see what is pending.
    """

    # cache: package -> prj, ver, rev, req, rst

    def label(self):
        return "submit requests"

    def __init__(self, service, project):
        self.service = service
        self.project = project
        self._pkgversions = {}

    def packages(self):
        raise Exception('No package list')
        # As version() now either shows a new or the last accepted request,
        # caching all requests of a project would be too expensive. Version()
        # now directly retrieves the requests for a given package.

    def version(self, package):
	d = self.cacheVersion( package )
	#ret = "%s\nrev %s\n%s\n#%s" % ( d.get( 'ver', '-' ), d.get( 'rev', '-' ), d.get( 'prj', 'UNKNOWN PRJ' ), d.get( 'req', '-' ) )
	ret = d.get( 'ver', '-' )
	if d.has_key( 'rev' ):
	  ret = "%s\nrev %s" % ( ret, d['rev'] )
	if d.has_key( 'req' ):
	  ret = "%s\n#%s" % ( ret, d['req'] )
	  if d.has_key( 'rst' ):
	    ret = "%s (%s)" % ( ret, d['rst'] )
	return ret

    def cacheVersion(self, package):
	if self._pkgversions.has_key( package ):
	  return self._pkgversions[package]

	self._pkgversions[package] = {}
	d = self._pkgversions[package]

        try:
            from xml.etree import cElementTree as ET
        except ImportError:
            import cElementTree as ET

        import osc.core
        key = self.service + "/" + self.project
        ret = None

        # first check for new requests
	rqlist = osc.core.get_request_list(self.service, self.project, package, '', req_state=('new','review'), req_type='submit' )
        rqlist.reverse()
        for request in rqlist:
          for req in request.actions:
            if req.src_package == package:
                # now look for the revision in the history to figure out the version
                # ret = "rev %s\n#%s (%s)" % (req.src_rev,request.reqid,request.state.name)
		d['prj'] = req.src_project
		#d['ver'] = '-'
		d['rev'] = req.src_rev
		d['req'] = request.reqid
		d['rst'] = request.state.name
                revisions = {}
                try:
                    # TODO: should be possible to directly query histpry for a specific revision '__history?rev=378'
                    u = osc.core.makeurl(self.service, ['source', req.src_project, package, '_history'])
                    f = osc.core.http_GET(u)
                    root = ET.parse(f).getroot()
                    revisions = root.findall('revision')
                    revisions.reverse()
                except urllib2.HTTPError, e:
                    print "Cannot get package info from: %s" % u
                    #exit(1)

                version = 0
                # maybe we can even figure out the version...
                for node in revisions:
                    rev = node.get('rev')
                    if rev == req.src_rev:
                        d['ver'] = node.find('version').text
                        return d
		return d

        # no new request then check last accepted: (TODO remove duplicate code here and loop above)
        rqlist = osc.core.get_request_list(self.service, self.project, package, '', req_state=('accepted',), req_type='submit' )
        rqlist.reverse()
        for request in rqlist:
          #print "REQ %s %s" % (request.reqid,request.state.name)
          for req in request.actions:
            #print "  A %s %s %s %s" % (req.type,req.src_project,req.dst_project,req.src_rev)
            if req.src_package == package:
                # now look for the revision in the history to figure out the version
                # ret = "rev %s\n#%s" % (req.src_rev,request.reqid)
		d['prj'] = req.src_project
		#d['ver'] = '-'
		d['rev'] = req.src_rev
		d['req'] = request.reqid
		#d['rst'] = ''
		revisions = {}
                try:
                    u = osc.core.makeurl(self.service, ['source', req.src_project, package, '_history'] )
                    f = osc.core.http_GET(u)
                    root = ET.parse(f).getroot()
                    revisions = root.findall('revision')
                    revisions.reverse()
                except urllib2.HTTPError, e:
                    print "Cannot get package info from: %s" % u
                    #exit(1)

                version = 0
                # maybe we can even figure out the version...
                for node in revisions:
                    rev = node.get('rev')
                    #print "%s %s" %(rev,req.src_rev)
                    if rev == req.src_rev:
                        d['ver'] = node.find('version').text
                        return d
                return d
        return d

    def mtime(self, package):
	return 0

    def changelog(self, package):
	d = self.cacheVersion( package )
	if d.has_key( 'prj' ) and d.has_key( 'rev' ):
	  return self.get_project_source_file( d['prj'], package, "%s.changes" % package, d['rev'] )
        return None

    def get_project_source_file(self, project, package, file, revision=None):
        """
        Returns the content of a source file
        and expand links if necessary

        if the file is not found, we fallback looking if the
        file is a linked package
        """
        import osc.core
        import osc.conf
        # There's got to be a more efficient way to do this :(

        query = None
        if revision:
            query = { 'rev': revision }
        # workaround
        u = None
        if query:
            u = osc.core.makeurl(self.service, ['source', project, package, file], query=query)
        else:
            u = osc.core.makeurl(self.service, ['source', project, package, file])

        try:
            f = osc.core.http_GET(u)
            return f.read()
        except urllib2.HTTPError, e:
            # ok may be it is a source link and this utterly sucks
            # but lets add some AI
            try:
                li = self.link_info(self.service, self.project, package)
                content = self.get_project_source_file(li.project, li.package, file, li.xsrcmd5)
                return content
            except urllib2.HTTPError, e:
                 # now really give up
                 print "Cannot get source file from: %s" % u
                 exit(1)

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
        if kind == "ibs" or kind == "ibssr":
            api = "https://api.suse.de"

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
