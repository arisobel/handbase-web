# Board Views

A board is a `ViewDefinition` (`view_type = board`), never a field type. Its
future definition will contain `group_by_field`; eligible source field types
are `single_select` and single `relation`. For a relation, columns derive from
the target records, and moving a card updates that source relation value.

The model already exists, but view API/persistence is intentionally unfinished,
so this phase does not expose a Board MVP or create parallel board persistence.
Future work includes column order, mobile horizontal navigation, RTL inline-start
ordering, drag/drop, search, filters and saved-view CRUD.
