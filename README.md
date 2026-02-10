# Agama Release Checker

This tool helps manage releases of [Agama][].

It tracks the progress of the code and resulting artifacts across:

1. The upstream development repo at GitHib
2. Open Build Service (OBS) both public (openSUSE) and internal (SLE) instances
3. Product ISO images at dowload.opensuse.org and download.suse.de

Taken into account are the transitional states, represented by OBS Submit
requests and Git Pull requests.

The specific projects, repos and packages are taken from a configuration file
so that this can be made useful for other teams and projects.

[Agama]: https://github.com/agama-project/agama/
