
See 'type: giteaproject' stages in config.yml

We will add a new report: Pull requests for giteaprojects. Use the tea tool mentined below.
stage.branch will match the base field of the PR.

Run: tea pr --help

Run: tea pr --login src.suse.de --repo pool/rubygem-agama-yast --output json \
            -f index,state,author,author-id,url,title,body,mergeable,base,base-commit,head,diff,patch,created,updated,deadline,assignees,milestone,labels,comments

Note that the login name is the hostname component of the giteaproject url.

Use a Research-Plan-Implement strategy.
