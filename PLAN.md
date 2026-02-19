For obsproject stages, we check the versions of the packages, with
PackagesInObsReport.

Now we are going to do a very similar report, except the same packages (with
spec and obsinfo files) are stored in Gitea. config.yml has a type:
giteaproject entry.

For giteaproject, convert the package URL to a SSH git remote like this (note the username)
url: https://src.suse.de/pool/agama
remote: gitea@src.suse.de:pool/agama.git

Giteaprojects contain big binary blobs so we want to avoid plain git clones.
Instead, do partial clones of only those files needed, with a shallow history.

Use a Reasearch-Plan-Implement strategy.
