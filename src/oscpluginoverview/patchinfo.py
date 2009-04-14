
# generate a patchinfo from a changelog

patchinfo_template = """\
SUMMARY: Describe the update
CATEGORY: recommended
PACKAGE: %(packages)s
PACKAGER: %(packager)s
SWAMPID:
SUBSWAMPID:
BUGZILLA: %(bugs)s
RATING: low
INDICATIONS: Every user should update
DISTRIBUTION: sle11-i586,sle11-ia64,sle11-ppc64,sle11-s390x,sle11-x86_64
DESCRIPTION:
%(description)s
"""

def patchinfo_from_changelog(changelog, packages, packager):
    """
    fills the bug and description information
    by reading a changelog, outputing a patchinfo
    file

    requires the package list, packager as input.
    """
    # string buffer for the patchinfo
    bugs = []
    
    from cStringIO import StringIO
    file_str = StringIO(changelog)
    description_str = StringIO()
    
    import re
    p = re.compile("bnc\s?#\s?(\d+)")
    pdate = re.compile("Mon|Tue|Wed|Thu|Fri|Sat|Sun")
    # save state if we are already on an item
    onitem = False
    for line in file_str:
        bugs.extend(p.findall(line))
        # see if the line is a added change
        if line[0] == '+':
            # skip
            # ++
            # ------------
            # Wed 16...
            if line[1] == '+':
                continue
            if line[1:5] == "----":
                continue
            if pdate.match(line[1:4]):
                continue
            # skip version lines
            if line[1:11] == "- version ":
                continue
            if re.compile("- \d+\.\d+\.\d+$").match(line[1:len(line)]):
                continue
            if line[1:2] == "\n":
                continue
            description_str.write(line[1:len(line)])

    args = { 'packages' : ','.join(packages),
             'packager' : packager,
             'bugs' : ','.join(list(set(bugs))),
             'description' : description_str.getvalue() }
    
    return patchinfo_template % args
