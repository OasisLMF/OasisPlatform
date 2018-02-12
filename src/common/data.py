class ExposureSummary(dict):
    def __init__(self, location, size, created_date):
        super(ExposureSummary, self).__init__({
            'location': location,
            'size': size,
            'created_date': created_date,
        })

    @property
    def location(self):
        return self['location']

    @property
    def size(self):
        return self['size']

    @property
    def created_date(self):
        return self['created_date']


class OutputsSummary(object):

    def __init__(self, location, size, created_date):
        self.location = location
        self.size = size
        self.created_date = created_date


class AnalysisStatus(object):

    def __init__(self, id, status, message, outputs_location):
        self.id = id
        self.status = status
        self.message = message
        self.outputs_location = outputs_location
