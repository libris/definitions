# Requires trld

TYPE=$1
FILE_PATH=$2
URL="https://libris-qa.kb.se/api/emm/full?selection=type:$TYPE&download=.ndjsonld.gz"

echo "Fetching from URL: $URL"

# Download from EMM
curl -o $FILE_PATH/libris-entities.gz $URL

# Decompress file
gzip -d $FILE_PATH/libris-entities.gz

# Transform with sed
sed -E 's/\{"@id":"https:\/\/libris-qa\.kb\.se\/[^"]+","@graph":/{\"@graph":/g; 
        s/\{"@id":"https:\/\/libris-qa\.kb\.se\/[^"]+","@context":/{\"@context":/g; 
        s/,"@context":\[null,"https:\/\/libris-qa\.kb\.se\/[^"]+"\]//g' $FILE_PATH/libris-entities > $FILE_PATH/libris-entities.ndjson

# Convert to TTL
cat $FILE_PATH/libris-entities.ndjson | trld -indjson -c -ottl $FILE_PATH/libris-entities.ndjson > $FILE_PATH/libris-entities.ttl