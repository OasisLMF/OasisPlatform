import six
from django.core.files import File
from io import StringIO, BytesIO
from model_mommy import mommy

from ..models import RelatedFile

FAKE_LOCATION_DATA = """PortNumber,AccNumber,LocNumber,IsTenant,BuildingID,CountryCode,Latitude,Longitude,StreetAddress,PostalCode,OccupancyCode,ConstructionCode,LocPerilsCovered,BuildingTIV,OtherTIV,ContentsTIV,BITIV,LocCurrency,OEDVersion
1,A11111,10002082046,1,1,GB,52.76698052,-0.895469856,1 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,220000,0,0,0,GBP,2.0.0
1,A11111,10002082047,1,1,GB,52.76697956,-0.89536613,2 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,790000,0,0,0,GBP,2.0.0
1,A11111,10002082048,1,1,GB,52.76697845,-0.895247587,3 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,160000,0,0,0,GBP,2.0.0
1,A11111,10002082049,1,1,GB,52.76696096,-0.895473908,4 ABINGDON ROAD,LE13 0HL,1050,5000,WW1,30000,0,0,0,GBP,2.0.0
"""


def fake_related_file(**kwargs):
    if 'content_type' not in kwargs:
        kwargs['content_type'] = 'text/csv'
    if 'file' not in kwargs:
        kwargs['file'] = File(StringIO(FAKE_LOCATION_DATA), 'filename')
    if isinstance(kwargs['file'], six.binary_type):
        kwargs['file'] = File(BytesIO(kwargs['file']), 'filename')
    elif isinstance(kwargs['file'], six.string_types):
        kwargs['file'] = File(BytesIO(kwargs['file'].encode()), 'filename')

    return mommy.make(RelatedFile, **kwargs)
