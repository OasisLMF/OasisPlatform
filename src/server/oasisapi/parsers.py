import jsonschema
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser

from .schemas.custom_swagger import load_json_schema


class JSONSchemaParser(JSONParser):
    """
        JSON schema validation examples:
            https://medium.com/@aleemsaadullah/adding-validation-support-for-jsonfield-in-django-2e26779dccc
            https://richardtier.com/2014/03/24/json-schema-validation-with-django-rest-framework/
    """
    def __init__(self, *args, **kwargs):
        schema_file = kwargs.pop('schema', None)
        self.schema = load_json_schema(schema_file)
        super().__init__(*args, **kwargs)

    def parse(self, stream, media_type=None, parser_context=None):
        data = super(JSONSchemaParser, self).parse(stream, media_type,
                                                   parser_context)
        try:
            jsonschema.validate(data, self.schema)
        except ValueError as error:
            raise ParseError(detail=error.message)
        else:
            return data            
