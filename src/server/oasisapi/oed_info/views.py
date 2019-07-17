from rest_framework import views
from rest_framework.response import Response

from oasislmf import __version__ as oasislmf_package_ver
from oasislmf.utils.peril import PERIL_GROUPS, PERILS
from oasislmf.utils.summary_levels import (
    SUMMARY_LEVEL_LOC,
    SUMMARY_LEVEL_ACC,
    OED_LOCATION_COLS,
    OED_ACCOUNT_COLS,
    OED_REINSINFO_COLS,
    OED_REINSSCOPE_COLS,
)

class PerilcodesView(views.APIView):
    """
    Return a list of all support OED peril codes in the oasislmf package
    """
    http_method_names = ['get']
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        peril_codes = {PERILS[p]['id']: {'desc': PERILS[p]['desc']} for p in PERILS.keys()}
        peril_groups = {PERIL_GROUPS[g]['id']: {
                                                'desc': PERIL_GROUPS[g]['desc'],
                                                'peril_ids': PERIL_GROUPS[g]['peril_ids']
                                                }  for g in PERIL_GROUPS.keys()}

        return Response({
            'oasislmf_version': oasislmf_package_ver,
            'peril_codes': peril_codes,
            'peril_groups': peril_groups
        })

class SummaryLevelsView(views.APIView):
    """
    Return a list of recommended OED columns for summary_level selection
    """
    def get(self, request):
        loc_summary_lvl = {k: v for k, v in OED_LOCATION_COLS.items() if k.lower() in SUMMARY_LEVEL_LOC}
        acc_summary_lvl = {k: v for k, v in OED_ACCOUNT_COLS.items() if k.lower() in SUMMARY_LEVEL_ACC}
        return Response({
            'oasislmf_version': oasislmf_package_ver,
            'location_file': loc_summary_lvl,
            'accounts_file': acc_summary_lvl,
        })

class OedAllColsView(views.APIView):
    """
    Return a list of all OED columns 
    """
    def get(self, request):
        return Response({
            'oasislmf_version': oasislmf_package_ver,
            'location_file': OED_LOCATION_COLS,
            'accounts_file': OED_ACCOUNT_COLS,
            'reinsurance_info_file': OED_REINSINFO_COLS,
            'reinsurance_scope_file': OED_REINSSCOPE_COLS,
        })
