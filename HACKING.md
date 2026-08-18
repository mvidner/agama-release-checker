This is written in Python, so that people and robots find it easy to read and
modify.

Specifically we target Python 3.12 or newer. On openSUSE Leap 16.0 we have 3.13
but on 15.6 where only 3.6 and 3.11 are available as RPMs, use uv.

Make use of ./agama-release-checker instead of calling python3 with arguments.

Read Makefile to see what checks the code should pass.
Run `make check` before committing.

In commit messages, first mention features and bugfixes, then separately
implementation details.

Use typing hints.

Write doc comments for classes, including
- what are the class responsibilities.

Write doc comments for functions.
