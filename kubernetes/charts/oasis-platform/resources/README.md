# Update default oasis OIDC configuration
## Keycloak Realms
1. Open a shell on the keycloak pod:

   ```
   kubectl exec -it deployment/keycloak bash
   ```

2. Do the export, this will actually bring up the server, but once it is up we can shut it down:

   ```
   # Start and wait for: ....Admin console listening on http://127.0.0.1:10090
   /opt/jboss/keycloak/bin/standalone.sh \
    -Djboss.socket.binding.port-offset=100 -Dkeycloak.migration.action=export \
    -Dkeycloak.migration.provider=singleFile \
    -Dkeycloak.migration.realmName=oasis \
    -Dkeycloak.migration.usersExportStrategy=REALM_FILE \
    -Dkeycloak.migration.file=/tmp/oasis-realm.json 
   ```

3. Download file from pod:

   ```
   # Get the pod name:
   PN=$(kubectl get pods -l app=keycloak --no-headers -o custom-columns=":metadata.name")
   
   # Download the export:
   kubectl cp $PN:/tmp/oasis-realm.json oasis-realm.json
   ```

# Authentik Blueprints
Authentik does have the functionality to export blueprints, however these are often exported into a large, unordered yaml file containing all default authentik configuration data, and everything is linked together by random primary keys, making this file essentially not human readable and difficult to cut down and edit.

The best way to modify Authentiks configuration is to directly edit the `blueprints/oasis-blueprint.yaml` file, using the [default github blueprints](https://github.com/goauthentik/authentik/tree/main/blueprints) as an example.