#!/bin/bash
endpoint=$1
queryfile=$2

curl -s $endpoint -HAccept:text/turtle --data-urlencode "query@$queryfile"
