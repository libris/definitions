#!/usr/bin/env bash
set -euo pipefail

cd $(dirname $0)/../../
(
  oxrq -f examples/typenormalization/saogf-insert-missing.ru source/categories/{contentforms,contentgenres,genreforms,marcmatches,marcmatches-music}.ttl
  cat examples/typenormalization/saogf-patches.ttl
) | oxrq -itrig -f examples/typenormalization/saogf-from-ktg.rq | trld -ittl -rottl
