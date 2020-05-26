#!/bin/bash
set -x
awslocal s3 mb s3://example-bucket
awslocal s3api put-bucket-acl --bucket example-bucket --acl public-read-write
set +x
