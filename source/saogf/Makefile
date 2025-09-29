.PHONY: saogf

saogf: build/saogf-new.ttl build/saogf-patch.ttl

build/saogf-new.ttl: build saogf-construct-missing.rq saogf-from-ktg.rq
	oxrq -f saogf-construct-missing.rq genres.ttl genreforms.ttl | oxrq -f saogf-from-ktg.rq | trld -ittl -ottl > $@.TMP
	mv $@.TMP $@

build/saogf-patch.ttl: build saogf-from-ktg.rq
	oxrq -f saogf-from-ktg.rq genres.ttl genreforms.ttl marcmatches.ttl marcmatches-music.ttl saogf-patches.ttl | trld -ittl -ottl > $@.TMP
	mv $@.TMP $@

#build/barngf-new.ttl: build

#test: saogf cache/saogf.ttl
# TODO: Check no redundant broader: 'select ?s ?b { ?s skos:broader ?b filter exists { ?s :broader ?b } }'

cache/saogf.ttl: cache get-all-of-saogf.sh
	./get-all-of-saogf.sh
	#curl -s https://libris.kb.se/sparql -HAccept:text/turtle --data-urlencode 'query=PREFIX : <https://id.kb.se/vocab/> CONSTRUCT WHERE { ?a a :GenreForm ; :inScheme <https://id.kb.se/term/saogf> ; :broader ?b }' -o $@

build:
	mkdir -p build

cache:
	mkdir -p cache
