# norootforbuild

# We need this for /var/lib/osc-plugins ownership
BuildRequires:  osc
Name:           osc-plugin-overview
Version:        0.1.0
Release:        1
License:        GPL
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
Source0:        osc-plugin-overview-%{version}.tar.gz
Group:          Development/Tools/Other
Summary:        Plugins for the osc tool to assist comparing versions across repositories
URL:            http://en.opensuse.org/Build_Service/osc_plugins/Overview
BuildArch:      noarch
Requires:       osc

%description
This package is a collection of osc plugins to assist comparison of build service
repositories against other repositories or even upstream repositories.

See http://en.opensuse.org/Build_Service/osc_plugins/Overview for an idea of what we are trying to achieve and http://en.opensuse.org/Build_Service/CLI for general information about osc.

%prep
%setup

%build
#%configure
#%makeinstall

%install

%clean
rm -rf "$RPM_BUILD_ROOT"

%files
%defattr(-,root,root)
%doc README AUTHORS NEWS COPYING
/var/lib/osc-plugins/*.py

%changelog