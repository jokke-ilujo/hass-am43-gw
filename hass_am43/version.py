import pbr.version

version_info = pbr.version.VersionInfo('hass_am43')
version_string = version_info.version_string


def version():
    return version_string
