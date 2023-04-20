source/cc-licenses.ttl: source/construct-cc-license-data.rq
	cat source/cc-licenses-header.txt > $@
	(echo https://creativecommons.org/publicdomain/mark/1.0/ && echo https://creativecommons.org/publicdomain/mark/1.0/deed.sv && curl -sL https://creativecommons.org/about/cclicenses/ | sed -nE 's!.*<a href="([^"]+)"><img .*!\1\n\1deed.sv!p') | xargs python3 scripts/construct.py $^ >> $@
