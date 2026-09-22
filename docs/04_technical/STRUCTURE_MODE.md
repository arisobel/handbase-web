# Structure Mode

Structure Mode is a browser-local UI preference, keyed per workspace in
`localStorage`; it is not a workspace setting and is never authorization.
Only members with `change_structure` see its compact control. Data Mode is the
default and hides new-table, field-management and table-structure entry points.
The existing API capability checks remain authoritative.

Structural actions use the semantic `actionStructure` visual treatment;
record actions retain the primary/data treatment. Layout uses logical CSS, so
the same control placement works in RTL.
