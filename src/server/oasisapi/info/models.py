from ods_tools import __version__ as ods_version
import logging
import os


def get_components_version():
    components_versions = {
        'ods_version': ods_version
    }

    try:
        from ods_tools.oed.oed_schema import OedSchema
        if os.environ.get("OASIS_OED_SCHEMA_VERSION", False):
            components_versions['oed_version'] = os.environ["OASIS_OED_SCHEMA_VERSION"]
        else:
            components_versions['oed_version'] = OedSchema.from_oed_schema_info(oed_schema_info=None).schema['version']

    except Exception:
        logging.exception("Failed to get OED version info")

    return components_versions
