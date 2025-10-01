# TODO: Requires *dev*-installations of trld and oxrq;
# replace with pyoxigraph-based script?
# This is a "one-off" conversion though; so we might get by...

.PHONY: saogf

saogf: build/saogf-patch.ttl

build/saogf-patch.ttl: build saogf-from-ktg.rq saogf-insert-missing.ru genres.ttl genreforms.ttl marcmatches.ttl marcmatches-music.ttl saogf-patches.ttl
	((cat genres.ttl genreforms.ttl marcmatches.ttl marcmatches-music.ttl ; oxrq -f saogf-insert-missing.ru genres.ttl genreforms.ttl) | oxrq -itrig -f saogf-from-ktg.rq ; cat saogf-patches.ttl > /dev/null ) | trld -ittl -rottl > $@.TMP # deactivated tentative patch with null redir!
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
