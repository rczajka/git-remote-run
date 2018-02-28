git-remote-run
==============

This package defines a `git-remote-run` command, which allows running
custom commands on a git remote.

This can be used, for example, to set up the actual remote repository,
as in:

.. code:: bash

 $ git remote add remote-repo user@server:path/to/repo
 $ git remote-run remote-repo -c '
     mkdir -p $REPO_DIR
     git init --bare $REPO_DIR
     echo echo it works! > $REPO_DIR/hooks/update
     chmod +x $REPO_DIR/hooks/update'
 Initialized empty Git repository in /home/user/path/to/repo/
 $ git push remote-repo master
 ...
 remote: it works!

See `git remote-run -h` for more options.


How does it work?
-----------------

`git-remote-run` doesn't attempt any parsing of the git remote URL
on its own, nor does it make assumptions about the transport used.
Instead, it relies on git's built-in ability to run commands on the
remote side.

Git uses this ability in its `git archive --remote=...` command, to
create an archive of a remote repository. We abuse this ability
a little bit by sending a custom script to run as the `--exec`
parameter.


Author
------

Radek Czajka


License
-------

This project is licensed under the MIT License – see the LICENSE file for details.
