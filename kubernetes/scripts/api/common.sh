
BASE_URL="http://localhost:8000"

ACCESS_TOKEN=$(curl -s -X POST "${BASE_URL}/access_token/" -H "accept: application/json" -H "Content-Type: application/json" \
  -d "{ \"username\": \"${OASIS_USER}\", \"password\": \"${OASIS_PASSWORD}\"}" | jq -r .access_token)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "Failed to authenticate"
  exit 1
fi

