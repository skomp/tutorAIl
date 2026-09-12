# Design

## Dead letter routing {#dead-letter-routing}

A record a consumer rejects is appended to a parallel stream named for the
original topic, with the rejection reason and the original offset attached. The
original partition is never rewritten and its offsets never move.
