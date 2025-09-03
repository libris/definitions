prefix owl: <http://www.w3.org/2002/07/owl#>
prefix skos: <http://www.w3.org/2004/02/skos/core#>
prefix saogf: <https://id.kb.se/term/saogf/>
prefix ktg: <https://id.kb.se/term/ktg/>
prefix : <https://id.kb.se/vocab/>

insert {
  ?s skos:exactMatch ?new_saogf_match ;
    skos:editorialNote "CONSTRUCTED" .
} where {
  ?s ?p ?o .

  filter not exists {
    ?s skos:exactMatch ?saogf_s .
    filter strstarts(str(?s), str(ktg:))
    filter strstarts(str(?saogf_s), str(saogf:))
  }

  ?s skos:prefLabel|:singularLabel ?label .
  filter(langmatches(lang(?label), 'sv'))

  bind(IRI(concat(str(saogf:),
            encode_for_uri(?label))) as ?new_saogf_match)
}
