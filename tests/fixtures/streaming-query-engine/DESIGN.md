# Design

## Plan shape {#plan-shape}

A query compiles to a tree of operators, each pulling from its children. A
bounded query is the same tree with a fixed upper offset; a continuous query is
the same tree with no upper bound and a blocking source.

## Window model {#window-model}

A window is a half-open interval over event time. A record arriving after its
window emitted is a late record, and the engine's answer to it is declared per
query rather than globally.
