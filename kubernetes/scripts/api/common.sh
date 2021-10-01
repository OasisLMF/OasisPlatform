
BASE_URL="https://api.oasis.local"
CURL="curl.exe -sk"

if [ -z "$OASIS_USERNAME" ] || [ -z "$OASIS_PASSWORD" ]; then
  echo "Set username and password as environment variables:"
  echo ""
  echo "export OASIS_USERNAME=admin"
  echo "export OASIS_PASSWORD=password"
  exit
fi

ACCESS_TOKEN=$($CURL -X POST "${BASE_URL}/access_token/" -H "accept: application/json" -H "Content-Type: application/json" \
  -d "{ \"username\": \"${OASIS_USERNAME}\", \"password\": \"${OASIS_PASSWORD}\"}" | jq -r '.access_token // empty')

if [ -z "$ACCESS_TOKEN" ]; then
  echo "Failed to authenticate"
  exit 1
fi

CAH="Authorization: Bearer ${ACCESS_TOKEN}"
