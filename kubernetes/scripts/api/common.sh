set -e
set -o pipefail

SCRIPT_DIR=$(dirname $0)
CURL="curl -sk"
TMP_PATH="/tmp/"

#if [ -f "/mnt/c/WINDOWS/system32/curl.exe" ]; then
#  CURL="${CURL//curl/curl.exe}"
#  TMP_PATH="/mnt/c/tmp/"
#fi

OASIS_SERVICE_USERNAME_OR_ID="${OASIS_SERVICE_USERNAME_OR_ID:-oasis-service}"
OASIS_SERVICE_PASSWORD_OR_SECRET="${OASIS_SERVICE_PASSWORD_OR_SECRET:-serviceNotSoSecret}"
OASIS_USE_OIDC="${OASIS_USE_OIDC:-1}"
API_URL="${OASIS_API_URL:-https://ui.oasis.local/api}"
OASIS_AUTH_API="${OASIS_AUTH_API:-1}"
KEYCLOAK_TOKEN_URL="${KEYCLOAK_TOKEN_URL:-https://ui.oasis.local/auth/realms/oasis/protocol/openid-connect/token}"
CLIENT_ID=oasis-server
CLIENT_SECRET=e4f4fb25-2250-4210-a7d6-9b16c3d2ab77

if [ "$OASIS_USE_OIDC" == "true" ]; then
  DATA="{\"client_id\": \"${OASIS_SERVICE_USERNAME_OR_ID}\", \"client_secret\": \"${OASIS_SERVICE_PASSWORD_OR_SECRET}\"}"
else
  DATA="{\"username\": \"${OASIS_SERVICE_USERNAME_OR_ID}\", \"password\": \"${OASIS_SERVICE_PASSWORD_OR_SECRET}\"}"
fi

if [ "$OASIS_AUTH_API" == "1" ]; then
  R="$($CURL -X POST "${API_URL}/access_token/" -H "accept: application/json" -H "Content-Type: application/json" -d "$DATA")"
  ACCESS_TOKEN=$(echo "$R" | jq -r '.access_token // empty')
else
  if [ "$OASIS_USE_OIDC" == "true" ]; then
    R="$($CURL --data-urlencode "grant_type=client_credentials" --data-urlencode "client_id=$CLIENT_ID" --data-urlencode "client_secret=$CLIENT_SECRET"  "$KEYCLOAK_TOKEN_URL")"
  else
    R="$($CURL --data-urlencode "grant_type=password" --data-urlencode --data-urlencode "username=$OASIS_SERVICE_USERNAME_OR_ID" --data-urlencode "password=$OASIS_SERVICE_PASSWORD_OR_SECRET" "$KEYCLOAK_TOKEN_URL")"
  fi
  ACCESS_TOKEN=$(echo "$R" | jq -r '.access_token // empty')
fi

if [ -z "$ACCESS_TOKEN" ]; then
  echo "Failed to authenticate:"
  echo "$R"
  exit 1
fi

CAH="Authorization: Bearer ${ACCESS_TOKEN}"

winpath() {
  if [[ "$TMP_PATH" == /mnt/c/* ]]; then
    echo "$1" | sed 's,^/mnt/c/,C:\\,' | sed 's,/,\\,g'
  else
    echo "$1"
  fi
}

curlf() {
  OUTPUT_FILE=$(mktemp -p $TMP_PATH)
  HTTP_CODE=$($CURL --output "$(winpath $OUTPUT_FILE)" --write-out "%{http_code}" -H "Authorization: Bearer ${ACCESS_TOKEN}" "$@")
  if [[ ${HTTP_CODE} -lt 200 || ${HTTP_CODE} -gt 299 ]]; then
    >&2 echo "Http code: ${HTTP_CODE}"
    >&2 cat "$OUTPUT_FILE"
    rm -f "$OUTPUT_FILE"
    return 22
  fi
  cat "$OUTPUT_FILE"
  rm -f "$OUTPUT_FILE"
}
