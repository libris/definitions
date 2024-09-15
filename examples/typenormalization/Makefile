test: cache/saogf.ttl
	python test_categories.py

cache/saogf.ttl: cache
	curl -s https://libris.kb.se/sparql -HAccept:text/turtle --data-urlencode 'query=PREFIX : <https://id.kb.se/vocab/> CONSTRUCT WHERE { ?a a :GenreForm ; :inScheme <https://id.kb.se/term/saogf> ; :broader ?b }' -o $@
cache:
	mkdir -p cache
