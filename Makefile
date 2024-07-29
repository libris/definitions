source/cc-licenses.ttl: source/construct-cc-license-data.rq
	cat source/cc-licenses-header.txt > $@
	(echo https://creativecommons.org/publicdomain/mark/1.0/ && echo https://creativecommons.org/publicdomain/mark/1.0/deed.sv && curl -sL https://creativecommons.org/about/cclicenses/ | sed -nE 's!.*<a href="([^"]+)"><img .*!\1\n\1deed.sv!p') | xargs python3 scripts/construct.py $^ >> $@

source/sab.ttl: scripts/extract_sab_data_from_docx.py cache/esab-2015_1.docx
	python3 $^ | trld -ijsonld -ottl > $@

source/sab/precoordinated.ttl: scripts/make_precoordinated_sab_terms.py source/sab.ttl cache/sab-usages.tsv.gz
	python3 $^ > $@ 2>logs/sab-unknown.tsv

cache/sab-usages.tsv.gz: scripts/sab-usages.rq
	curl -s https://libris.kb.se/sparql -HAccept:text/tab-separated-values --data-urlencode query@$^ | gzip - > /tmp/sab-usages.tsv.gz
	cp /tmp/sab-usages.tsv.gz $@
