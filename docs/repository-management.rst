Repository Management
=====================

Cloning the repository
----------------------

You can clone this repository from `GitHub <https://github.com/OasisLMF/OasisApi>`_ using HTTPS or SSH, but it is
recommended that that you use SSH: first ensure that you have generated
an SSH key pair on your local machine and add the public key of that
pair to your GitHub account (use the GitHub guide at
https://help.github.com/articles/connecting-to-github-with-ssh/). Then
run

::

    git clone --recursive git+ssh://git@github.com/OasisLMF/OasisApi

To clone over HTTPS use

::

    git clone --recursive https://github.com/OasisLMF/OasisApi

You may receive a password prompt - to bypass the password prompt use

::

    git clone --recursive https://<GitHub user name:GitHub password>@github.com/OasisLMF/OasisApi

The ``--recursive`` option ensures the cloned repository contains the
necessary Oasis repositories `oasis_utils <https://github.com/OasisLMF/oasis_utils>`_  and
`OasisAPIClient <https://github.com/OasisLMF/OasisAPIClient>`_  as Git submodules.

Managing the submodules
-----------------------

Run the command

::

    git submodule

to list the submodules (latest commit IDs, paths and branches). If any
are missing then you can add them using

::

    git submodule add <submodule GitHub repo URL> <local path/destination>

It is a quirk of Git that the first time you clone a repository with
submodules they will be checked out as commits not branches, which is
not what you want. You should run the command

::

    git submodule foreach 'git checkout master'

to ensure that the submodules are checked out on the ``master``
branches.

If you’ve already cloned the repository and wish to update the
submodules (all at once) in your working directory from their GitHub
repositories then run

::

    git submodule foreach 'git pull origin'

You can also update the submodules individually by pulling from within
them.

Unless you’ve been given read access to this repository on GitHub (via
an OasisLMF organizational team) you should not make any local changes
to these submodules because you have read-only access to their GitHub
repositories. So submodule changes can only propagate from GitHub to
your local repository. To detect these changes you can run
``git status -uno`` and to commit them you can add the paths and commit
them in the normal way.