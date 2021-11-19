set -e
set -o pipefail


API_URL="https://api.oasis.local"
#API_URL="http://localhost:8000"
SCRIPT_DIR=$(dirname $0)
CURL="curl -sk"
TMP_PATH="/tmp/"

KEYCLOAK_TOKEN_URL="https://ui.oasis.local/auth/realms/oasis/protocol/openid-connect/token"
CLIENT_ID=oasis-server
CLIENT_SECRET=e4f4fb25-2250-4210-a7d6-9b16c3d2ab77

if [ -f "/mnt/c/WINDOWS/system32/curl.exe" ]; then
  CURL="${CURL//curl/curl.exe}"
  TMP_PATH="/mnt/c/tmp/"
fi

if [ -z "$OASIS_USERNAME" ] || [ -z "$OASIS_PASSWORD" ]; then
  echo "Set username and password as environment variables:"
  echo ""
  echo "export OASIS_USERNAME=admin"
  echo "export OASIS_PASSWORD=password"
  exit
fi

USE_OASIS_API=1

if [ "$USE_OASIS_API" == "1" ]; then
  R="$($CURL -X POST "${API_URL}/access_token/" -H "accept: application/json" -H "Content-Type: application/json" \
         -d "{ \"username\": \"${OASIS_USERNAME}\", \"password\": \"${OASIS_PASSWORD}\"}")"
  ACCESS_TOKEN=$(echo "$R" | jq -r '.access_token // empty')
else
  R="$($CURL --data-urlencode "grant_type=password" --data-urlencode "client_id=$CLIENT_ID" --data-urlencode "client_secret=$CLIENT_SECRET" --data-urlencode "username=$OASIS_USERNAME" --data-urlencode "password=$OASIS_PASSWORD" "$KEYCLOAK_TOKEN_URL")"
  ACCESS_TOKEN=$(echo "$R" | jq -r '.access_token // empty')
fi

if [ -z "$ACCESS_TOKEN" ]; then
  echo "Failed to authenticate:"
  echo "$R"
  exit 1
fi

CAH="Authorization: Bearer ${ACCESS_TOKEN}"

winpath() {
  if [[ "$TMP_PATH" == "/mnt/c/*" ]]; then
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
