from hypothesis import settings

# Global Hypothesis test settings
settings.register_profile("fast", max_examples=30, database=None)
settings.load_profile("fast")
