class ExposureSummary(object):
   def __init__(self):
       self.location = ""
       self.size = 0
       self.created_date = ""
   def __init__(self, location, size, created_date):
       self.location = location
       self.size = size
       self.created_date = created_date

class OutputsSummary(object):
   def __init__(self):
       self.location = ""
       self.size = 0
       self.created_date = ""
   def __init__(self, location, size, created_date):
       self.location = location
       self.size = size
       self.created_date = created_date

class AnalysisStatus(object):
   def __init__(self):
       self.id = -1
       self.status = ""
       self.message = ""
       self.outputs_location = ""
   def __init__(self, id, status, message, outputs_location):
       self.id = id
       self.status = status
       self.message = message
       self.outputs_location = outputs_location