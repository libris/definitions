prefix owl: <http://www.w3.org/2002/07/owl#>
prefix skos: <http://www.w3.org/2004/02/skos/core#>
prefix div: <https://id.kb.se/term/div/>
prefix saogf: <https://id.kb.se/term/saogf/>
prefix barngf: <https://id.kb.se/term/barngf/>
prefix ktg: <https://id.kb.se/term/ktg/>
prefix : <https://id.kb.se/vocab/>

insert {
  ?s skos:exactMatch ?new_mapped_match ;
    :inCollection div:constructed .
} where {
  values ?prefix { saogf: }

  ?s ?p ?o .

  filter not exists {
    ?s skos:exactMatch ?mapped_s .
    filter strstarts(str(?s), str(ktg:))
    filter strstarts(str(?mapped_s), str(?prefix))
  }

  ?s skos:prefLabel ?label .
  filter(langmatches(lang(?label), 'sv'))

  bind(IRI(concat(str(?prefix),
            encode_for_uri(?label))) as ?new_mapped_match)
}
