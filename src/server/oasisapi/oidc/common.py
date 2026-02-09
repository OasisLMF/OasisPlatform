import os
from urllib3.util.connection import create_connection as urllib3_create_connection


def auth_server_create_connection(address, *args, **kwargs):
    """
    Wrap urllib3's create_connection to replace authentication server (e.g. keycloak/authentik) external host
    with its internal IP (Ingress address)

    The authentication server is bound to a specific hostname which requires us to use the same url to query authentication server in backend that is
    used in the UI for authentication (the JWT will contain the authenticaiton URL). We can't access the external ingress
    hostname but we can remap map it in this function.

    The kubernetes chart will export these two ENV vars
      ❯ export INGRESS_EXTERNAL_HOST='ui.oasis.local'
      ❯ export INGRESS_INTERNAL_HOST='10.107.69.196'

     replace 'INGRESS_EXTERNAL_HOST' with 'INGRESS_INTERNAL_HOST'
     and then call urllib3s connection
    """
    host, port = address

    external_host = os.getenv('INGRESS_EXTERNAL_HOST')
    internal_host = os.getenv('INGRESS_INTERNAL_HOST')

    if host == external_host:
        host = internal_host
    return urllib3_create_connection((host, port), *args, **kwargs)
