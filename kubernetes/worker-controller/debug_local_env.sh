# base local env file to run the worker controller code, Used for debugging.
# 
# Usage example:
#  1. deploy platform on mini-kube and open websocket 'kubectl port-forward deployment/oasis-websocket 8001:8001'
#  2. source this file, '. debug_local_env.sh'
#  3. install requirememts, 'pip install -r requirements.txt'
#  4. Run controller, './src/worker_controller.py'

export OASIS_USERNAME=admin
export OASIS_PASSWORD=password
export OASIS_CONTINUE_UPDATE_SCALING=0
export OASIS_NEVER_SHUTDOWN_FIXED_WORKERS=0
export OASIS_API_HOST=ui.oasis.local/api
export OASIS_API_PORT=''
export OASIS_WEBSOCKET_HOST=ui.oasis.local/ws
export OASIS_WEBSOCKET_PORT=''
export OASIS_CLUSTER_NAMESPACE=default
export CLUSTER=local
export OASIS_TOTAL_WORKER_LIMIT=10
export OASIS_PRIORITIZED_MODELS_LIMIT=10
