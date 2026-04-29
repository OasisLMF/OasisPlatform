__all__ = [
    'PERILS',
    'PERIL_GROUPS',
]
from ods_tools.oed import OedSchema
import os


def get_peril_info_from_schema(oed_version='latest version'):
    '''
    Get perils and peril_groups info from OedSchema.

    Args:
        oed_version (str): The version of OedSchema, default to `latest version`.
    '''
    oed_schema = OedSchema.from_oed_schema_info(
        oed_schema_info=os.environ.get("OASIS_OED_SCHEMA_INFO", 'latest version'))

    peril_info = oed_schema.schema['perils']['info']
    peril_covered = oed_schema.schema['perils']['covered']

    peril_groups = {}
    perils = {}
    for peril_code, peril in peril_info.items():
        if peril['Grouped PerilCode'] == 'Yes':
            peril_groups[peril_code] = {'id': peril_code, 'desc': peril['Peril Description'],
                                        'peril_ids': peril_covered[peril_code]}
        else:
            perils[peril_code] = {'id': peril_code,
                                  'desc': peril['Peril Description']}

    return perils, peril_groups


PERILS, PERIL_GROUPS = get_peril_info_from_schema()
