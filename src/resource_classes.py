class ExposureSummary(object):
   def __init__(self):
       self.location = ""
       self.size = 0
       self.created_date = ""
   def __init__(self, location, size, created_date):
       self.location = location
       self.size = size
       self.created_date = created_date

class ResultsSummary(object):
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
       selef.results_summary = None

   def __init__(self, id, status, message, results_summary):
       self.id = id
       self.status = status
       self.message = message
       selef.results_summary = results_summary