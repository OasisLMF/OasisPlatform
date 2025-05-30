def verify_model_scaling(model):
    if model.run_mode:
        if model.run_mode.lower() == "v1":
            if model.scaling_options.scaling_strategy not in ["QUEUE_LOAD", "FIXED_WORKERS", None]:
                raise ValueError("Model has invalid scaling setting")
