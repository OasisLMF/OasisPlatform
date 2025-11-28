from ods_tools import __version__ as ods_version
import logging
import os


def get_components_version():
    components_versions = {
        'ods_version': ods_version
    }

    try:
        from ods_tools.oed.oed_schema import OedSchema
        components_versions['oed_version'] = OedSchema.from_oed_schema_info(
            oed_schema_info=os.environ.get("OASIS_OED_SCHEMA_INFO", None)
        ).schema['version']

    except Exception:
        logging.exception("Failed to get OED version info")

    return components_versions
