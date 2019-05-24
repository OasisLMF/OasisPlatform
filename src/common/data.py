STORED_FILENAME = "stored_filename"
ORIGINAL_FILENAME = "original_filename"


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


class AnalysisStatus(dict):
    def __init__(self, id, status, message, outputs_location):
        super(AnalysisStatus, self).__init__({
            'id': id,
            'status': status,
            'message': message,
            'outputs_location': outputs_location,
        })

    @property
    def id(self):
        return self['id']

    @property
    def status(self):
        return self['status']

    @status.setter
    def status(self, val):
        self['status'] = val

    @property
    def message(self):
        return self['message']

    @property
    def outputs_location(self):
        return self['outputs_location']
