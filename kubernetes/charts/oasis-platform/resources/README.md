# Update default oasis realm

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
