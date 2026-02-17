Read HACKING.md.

When done with a task, do not foget to suggest updates to the documentation.

Take care about command quoting.
In particular, when making a commit message, know that backquotes used for code
in markdown mean command substitution in the shell, so use single quotes
at the outer level.

Do not remove existing hashbangs from script headers.

Python code is using the Black formatter. Use [its style][black-style] when writing,
and run `black --diff` before committing.

[black-style]: https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html
