from rest_framework import views
from rest_framework.response import Response
from oasislmf.utils.peril import PERIL_GROUPS, PERILS


class PerilcodesView(views.APIView):
    """
    Return a list of all support OED peril codes in the oasislmf package
    """
    http_method_names = ['get']
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({**dict(PERILS), **dict(PERIL_GROUPS)})



