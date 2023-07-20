#!/bin/bash

set -x

# Swagger codegen
SWAGGER_CODEGEN_v2="https://repo1.maven.org/maven2/io/swagger/codegen/v3/swagger-codegen-cli/3.0.43/swagger-codegen-cli-3.0.43.jar"
CODEGEN_EXEC_v2='swagger-codegen-cli-2.jar'
SWAGGER_CODEGEN_v3="https://repo1.maven.org/maven2/io/swagger/swagger-codegen-cli/2.4.32/swagger-codegen-cli-2.4.32.jar"
CODEGEN_EXEC_v3='swagger-codegen-cli-3.jar'

# run opts
OASIS_VER=1.28.0
OPENAPI_JSON_URL="https://github.com/OasisLMF/OasisPlatform/releases/download/$OASIS_VER/openapi-schema-$OASIS_VER.json"
OPENAPI_JSON_FILE="openapi-schema-$OASIS_VER.json"
OUTPUT_DIRECTORY="./"
GENERATOR_NAME="html2"

# Download current stable 2.x.x branch (Swagger and OpenAPI version 2)
if [[ ! -f $CODEGEN_EXEC_v2 ]]; then 
    wget $SWAGGER_CODEGEN_v2 -O $CODEGEN_EXEC_v2
fi 

# Download current stable 3.x.x branch (OpenAPI version 3)
if [[ ! -f $CODEGEN_EXEC_v3 ]]; then 
    wget $SWAGGER_CODEGEN_v3 -O $CODEGEN_EXEC_v3
fi 

# Download OasisPlatform OpenAPI schema
if [[ ! -f $OPENAPI_JSON_FILE ]]; then
    wget $OPENAPI_JSON_URL -O $OPENAPI_JSON_FILE
fi 


# download contents of this to `./template` and edit 
https://github.com/swagger-api/swagger-codegen-generators/tree/master/src/main/resources/handlebars/htmlDocs2
HTML_TEMPLATE="./oasis_template"


# Run Swagger Codegen to generate the HTML2 client
java -jar $CODEGEN_EXEC_v2 generate \
  -i $OPENAPI_JSON_FILE \
  -l $GENERATOR_NAME \
  -o $OUTPUT_DIRECTORY \
  --template-dir $HTML_TEMPLATE
