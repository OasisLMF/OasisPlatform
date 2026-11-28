"""Extracting shared run data into a worker's run directory."""
import os
import shutil
from pathlib import Path

import filelock


def extract_tar_once(filestore, filestore_ref, dst, storage_subdir=''):
    """Extract filestore_ref into dst, unless a previous extraction already completed.

    Several tasks on one worker share dst, so a file lock lets only one extract it. The archive
    is extracted into ``<dst>.partial`` and renamed to dst only once extraction succeeds, so a
    failed extraction never leaves a partial dst behind. Previously dst was extracted in place
    and its mere existence meant "done", so a run that failed part way (e.g. OasisPlatform#1500)
    left every retry running on an incomplete directory.

    Args:
        filestore: storage with ``extract(reference, target_dir, storage_subdir)``
        filestore_ref (str): reference of the archive in the filestore
        dst (str): directory to extract into
        storage_subdir (str): filestore subdirectory of the archive
    """
    with filelock.FileLock(f'{dst}.lock'):
        if Path(dst).exists():
            return
        partial = f'{dst}.partial'
        shutil.rmtree(partial, ignore_errors=True)
        try:
            filestore.extract(filestore_ref, partial, storage_subdir)
            os.rename(partial, dst)
        except BaseException:
            shutil.rmtree(partial, ignore_errors=True)
            raise
