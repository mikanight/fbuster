Name:           fedorabooster
Version:        0.0.1
Release:        1.alfa%{?dist}
Summary:        System maintenance utility for Fedora Linux

License:        MIT
URL:            https://github.com/mikanight/fbuster
Source0:        %{url}/archive/v%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       git
Requires:       hicolor-icon-theme

%description
Fedora Booster is a GTK4/Libadwaita desktop utility for configuring
and maintaining Fedora Linux. It provides a tabbed interface for
system tweaks, app installation (DNF/Flatpak), GNOME extension
management, terminal setup (Ghostty/ZSH), AMD Radeon tuning,
DaVinci Resolve setup, System76 Scheduler, and TimeSync (BorgBackup).

Based on ALT Booster by PLAFON, adapted for Fedora.

%prep
%autosetup -n fbuster-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install

# Desktop file
mkdir -p %{buildroot}%{_datadir}/applications/
desktop-file-install \
    --dir=%{buildroot}%{_datadir}/applications \
    %{_builddir}/fbuster-%{version}/fedorabooster.desktop

# Icons
for _size in 16x16 24x24 32x32 48x64 64x64 96x96 128x128 256x256 512x512; do
    _dir=%{buildroot}%{_datadir}/icons/hicolor/${_size}/apps
    mkdir -p $_dir
done
install -m 644 %{_builddir}/fbuster-%{version}/icons/fedorabooster.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/fedorabooster.svg

# Hicolor sub-icons
for _svg in %{_builddir}/fbuster-%{version}/icons/hicolor/scalable/apps/*.svg; do
    install -m 644 $_svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/
done

for _svg in %{_builddir}/fbuster-%{version}/icons/hicolor/scalable/devices/*.svg; do
    install -m 644 $_svg %{buildroot}%{_datadir}/icons/hicolor/scalable/devices/
done

# Help (Mallard)
mkdir -p %{buildroot}%{_datadir}/help/C/%{name}/
cp -r %{_builddir}/fbuster-%{version}/help/C/* %{buildroot}%{_datadir}/help/C/%{name}/

%check
%pyproject_check_import -e '*.common'

%post
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    /usr/bin/gtk-update-icon-cache -q %{_datadir}/icons/hicolor || :
fi
update-desktop-database -q %{_datadir}/applications || :

%postun
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    /usr/bin/gtk-update-icon-cache -q %{_datadir}/icons/hicolor || :
fi
update-desktop-database -q %{_datadir}/applications || :

%files -f %{pyproject_files}
%doc README.md CHANGELOG.md
%license LICENSE
%{_datadir}/applications/fedorabooster.desktop
%{_datadir}/icons/hicolor/scalable/apps/fedorabooster.svg
%{_datadir}/icons/hicolor/scalable/apps/*.svg
%{_datadir}/icons/hicolor/scalable/devices/*.svg
%{_datadir}/help/C/%{name}/

%changelog
* Wed May 07 2026 Andrei Komissarov <mikanight@github> - 0.0.1-1.alfa
- Initial Fedora COPR build
- Adapted from ALT Booster for Fedora Linux
- System76 Scheduler via COPR, Ghostty terminal
- Security: pkexec command whitelist, shell script validation
