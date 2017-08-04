===========
Sphinx docs
===========

Setting up Sphinx
-----------------

This repository is enabled with `Sphinx <https://pypi.python.org/pypi/Sphinx>`_ documentation for the Python
modules, and the documentation is published to
https://oasislmf.github.io/OasisApi/ manually using the procedure
described below. (Note: GitHub pages is not enabled for this repository
because it contains the private repository `oasis_utils <https://github.com/OasisLMF/oasis_utils>`_ as a Git
submodule, which is incompatible with GitHub pages.)

Firstly, to work on the Sphinx docs for this package you must have
Sphinx installed on your system or in your ``virtualenv`` environment
(recommended).

You should also clone the `Oasis publication repository <https://github.com/OasisLMF/OasisLMF.github.io>`_.

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

Add and commit these files to the repository. Then copy the files to the Oasis API docs static subfolder in the publication repository using

::

    cp -R _build/html/* /path/to/your/OasisLMF.github.io/OasisApi/

Add and commit the new files in the publication repository, and GitHub
pages will automatically publish the new documents to the documentation
site https://oasislmf.github.io/OasisApi/.