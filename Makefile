source/cc-licenses.ttl: source/construct-cc-license-data.rq
	cat source/cc-licenses-header.txt > $@
	(echo https://creativecommons.org/publicdomain/mark/1.0/ && echo https://creativecommons.org/publicdomain/mark/1.0/deed.sv && curl -sL https://creativecommons.org/about/cclicenses/ | sed -nE 's!.*<a href="([^"]+)"><img .*!\1\n\1deed.sv!p') | xargs python3 scripts/construct.py $^ >> $@

source/sab.ttl: scripts/extract_sab_data_from_docx.py cache/esab-2015_1.docx
	python3 $^ | trld -ijsonld -ottl > $@
	# TODO 1: enhance with DDC-mappings: scripts/create_sab_skos_data.py +
	# ../librisxl/whelk-core/src/main/java/se/kb/libris/export/dewey/dewey_sab.txt
	# TODO 2: In XL, add precomposed usages (extract from usage in records)? See:
	# ../librisxl/marc_export/src/main/resources/se/kb/libris/export/sabrub.txt # precomposed
