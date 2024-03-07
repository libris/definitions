source/cc-licenses.ttl: source/construct-cc-license-data.rq
	cat source/cc-licenses-header.txt > $@
	(echo https://creativecommons.org/publicdomain/mark/1.0/ && echo https://creativecommons.org/publicdomain/mark/1.0/deed.sv && curl -sL https://creativecommons.org/about/cclicenses/ | sed -nE 's!.*<a href="([^"]+)"><img .*!\1\n\1deed.sv!p') | xargs python3 scripts/construct.py $^ >> $@

source/sab.ttl: scripts/extract_sab_data_from_docx.py cache/esab-2015_1.docx
	python3 $^ | trld -ijsonld -ottl > $@
	# TODO 1: enhance with DDC-mappings: scripts/create_sab_skos_data.py +
	# ../librisxl/whelk-core/src/main/java/se/kb/libris/export/dewey/dewey_sab.txt
	# TODO 2: In XL, add precomposed usages (extract from usage in records)? See:
	# ../librisxl/marc_export/src/main/resources/se/kb/libris/export/sabrub.txt # precomposed

cache/ssif.xlsx:
	curl https://www.uka.se/download/18.11258e6a184d17a7b2c2e5/1669982839699/Forskningsamnen-standard-2011.xlsx -o cache/ssif.xlsx

# See: <https://ask.libreoffice.org/t/cli-convert-ods-to-csv-with-semicolon-as-delimiter/5021/10>.
# * 9 = Tab
# * 90 = UTF-8
cache/ssif.csv: cache/ssif.xlsx
	libreoffice --headless --convert-to csv:"Text - txt - csv (StarCalc)":"9,ANSI,90" $^ --outdir cache/

source/ssif.jsonld: scripts/create_ssif_science_topic_data.py cache/ssif.csv
	python3 $^ > $@

source/ssif.ttl: source/ssif.jsonld
	trld $^ -o ttl > $@
