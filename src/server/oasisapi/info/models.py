from ods_tools import __version__ as ods_version
import logging


def get_components_version():
    components_versions = {
        'ods_version': ods_version
    }

    try:
        from ods_tools.oed.oed_schema import OedSchema
        OedSchemaData = OedSchema.from_oed_schema_info(oed_schema_info=None)
        components_versions['oed_version'] = OedSchemaData.schema['version']
    except Exception as _:
        logging.exception("Failed to get OED version info")

    return components_versions
