This is written in Python, so that people and robots find it easy to read and
modify.

Specifically we target the Python platform that is available in
openSUSE Leap 15.6 and that is Python 3.6.

Make use of ./agama-release-checker instead of calling python3 with arguments.

Read Makefile to see what checks the code should pass.
Run `make check` before committing.

In commit messages, first mention features and bugfixes, then separately
implementation details.
