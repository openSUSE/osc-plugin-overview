
# Introduction

Overview plugin allows you to build a table comparing versions in different sources including openSUSE build service projects.

[Original blog post](https://duncan.codes/2009/04/07/introducing-osc-plugin-overview.html).

# Installation

You can install from [openSUSE:Tools](https://software.opensuse.org/download/package?project=openSUSE:Tools&package=osc-plugin-overview).

# Contributing

Development is hosted on [github](https://github.com/openSUSE/osc-plugin-overview).

# Supported data sources

* Build service project ( obs://project )
* Build service pending submit requests against project ( obssr://project )
* Upstream gem repository ( gem://server )

# Examples

To use it, you call it with:

```console
osc overview groupviewname
```

The groupview is a ini file in ` ~/.osc-overview/viewname.ini`, A groupview contains one or more views, which are sections of the ini file.

Examples:

```
[openSUSE-11.1]
repos=obs://openSUSE:11.1,obs://zypp:Code11-Branch,obs://openSUSE:11.1:Update
packages=libzypp,zypper
```

This compares libzypp and zypper version from 3 different projects. The output is similar to:

```
** openSUSE-11.1 **
+------------------+------------------+------------------+------------------+
|     package      | obs://openSUSE:1 | obs://zypp:Code1 | obs://openSUSE:1 |
|                  |       1.1        |     1-Branch     |    1.1:Update    |
+==================+==================+==================+==================+
| libzypp          | 5.24.5           | 5.29.5           | 5.25.3           |
+------------------+------------------+------------------+------------------+
| zypper           | 1.0.2            | 1.0.8            | 1.0.5            |
+------------------+------------------+------------------+------------------+
```

Another example, is to compare versions with upstream:

```
[gems]
repos=obs://devel:languages:ruby:extensions,gem://gems.rubyforge.org
packages=*1
```

Here, you can see the package list uses `*1`, that means, fetch the package list from the first source being compared. Be careful to use `*1` with projects like openSUSE:Factory unless you really mean that. Usually you use the package list from the less common denominator across all sources.

The resulting table is:

```
** gems **
+-------------------------+-------------------------+-------------------------+
|         package         | obs://devel:languages:r | gem://gems.rubyforge.or |
|                         |     uby:extensions      |            g            |
+=========================+=========================+=========================+
| rubygem-hpricot         | 0.7                     | 0.8                     |
+-------------------------+-------------------------+-------------------------+
...
+-------------------------+-------------------------+-------------------------+
```

# Filters

## Only outdated packages

To only display a row, if certain repo contains a package older than any of the other repos, Add to the view definition:

```
filter.older={repoexpr}
```

`repoexpr` can be the repository in repos option, or a shortcut `$pos` (`$1` is the first one).

```
filter.older=$1
```

Example:

```
[gems]
repos=obs://devel:languages:ruby:extensions,gem://gems.rubyforge.org
packages=rubygem-hpricot
packages=*1
filter.older=$1
```

Will display only outdated packages with respect to the upstream gem server:

```
+-------------------------+-------------------------+-------------------------+          
|         package         | obs://devel:languages:r | gem://gems.rubyforge.or |          
|                         |     uby:extensions      |            g            |          
+=========================+=========================+=========================+          
| rubygem-commonwatir     | 0                       | 1.6.2                   |          
+-------------------------+-------------------------+-------------------------+          
| rubygem-erubis          | 2.6.2                   | 2.6.4                   |          
+-------------------------+-------------------------+-------------------------+          
| rubygem-facets          | 2.5.0                   | 2.5.1                   |          
+-------------------------+-------------------------+-------------------------+          
| rubygem-fastthread      | 1.0.1                   | 1.0.6                   |          
+-------------------------+-------------------------+-------------------------+ 
...
```

# Planed features

* filter by name
* other outputs, like .changes and patchinfo
* show a package only if certain column is the smallest version <font color="green">[DONE]</font>

# Use cases

## Upstream Maintainer

* Developer maintains 3 packages for openSUSE factory.
* All packages can be found upstream in freshmeat
* he maintains them in his home build service project
* He wants to see 3 columnns:
** What is upstream
** What he has packaged in his repository
** What he has submited to Factory
* He can use the filter.older feature and set his home project as base. Then he will be informed when the upstream column is newer
** In theory he would be informed if Factory has a newer version than his home project, but this is not an expected case.

## Maintenance

* Maintenance coordinator for a certain area
* Packages A,B,C,D,E present in openSUSE 11.1 GA
* Packages A,B,C, with bugfixes w/r to 11.1 versions come from one project in build service
* Packages D,E come from another developer, who keeps the updated versions in his home project.
* Coordinator wants to overview versions from GA, development projects, pending submissions to any of these packages to the 11.1 update repository and the update repository iteself.
* He wants to generate the .changes list from what is in the development project which are not yet in the update repository
* He wants to get a prototype of the PATCHINFO

*11.1 Updates*

| Package | 11.1 GA | repo1 | repo2 | Update submitted | Updates |
| ------- | ------- | ----- | ----- | ---------------- | ------- |
| A | 1.0 | 1.2 | - | - | 1.1 |
| B | 1.0 | 1.3 | - | - | -   |
| C | 1.0 | 1.2 | - | - | 1.1 |
| D | 2.0 | - | 2.2 | - | - |
| E | 2.0 | - | 2.3 | - | 2.1 |

