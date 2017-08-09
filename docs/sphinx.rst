Sphinx Docs
===========

This repository is enabled with Sphinx documentation for the Python
modules, and the documentation is published to
https://oasislmf.github.io/OasisApi/ manually using the procedure
described below. (Note: GitHub pages is not enabled for this repository
because it contains the private repositories `oasis_utils <https://github.com/OasisLMF/oasis_utils>`_ and `OasisAPIClient <https://github.com/OasisLMF/OasisAPIClient>`_  as a Git submodules, which is incompatible with GitHub pages.)


Setting up Sphinx
-----------------

Firstly, to work on the Sphinx docs for this package you must have
`Sphinx <https://pypi.python.org/pypi/Sphinx>`_ installed on your system or in your virtual environment
(`virtualenv` is recommended).

You should also clone the Oasis publication repository
`OasisLMF.github.io <https://github.com/OasisLMF/OasisLMF.github.io>`_.

Building and publishing
-----------------------

The Sphinx documentation source files are reStructuredText files, and
are contained in the ``docs`` subfolder, which also contains the Sphinx
configuration file ``conf.py`` and the ``Makefile`` for the build. To do
a new build make sure you are in the ``docs`` subfolder and run

::

    make html

You should see a new set of HTML files and assets in the ``_build/html``
subfolder (the build directory can be changed to ``docs`` itself in the
``Makefile`` but that is not recommended). The ``docs`` subfolder should
always contain the latest copy of the built HTML and assets so first
copy the files from ``_build/html`` to ``docs`` using

::

    cp -R _build/html/* .

Add and commit these files to the local repository, and then update the
remote repository on GitHub. Then copy the same files to the Oasis API
server docs static subfolder in the publication repository

::

    cp -R _build/html/* /path/to/your/OasisLMF.github.io/OasisApi/

Add and commit the new files in the publication repository, and then
update the remote repository on GitHub - GitHub pages will automatically
publish the new documents to the documentation site
https://oasislmf.github.io/OasisApi/.