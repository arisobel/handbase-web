# Relations

`relation` is a single-valued metadata field. Its `config.target_table_id`
names another `TableDefinition` in the same workspace; its stored JSONB value
is the related `Record` UUID. No user-defined SQL foreign-key columns exist.

The record service validates UUID shape, existence and target table. Deletion
uses RESTRICT: a referenced record returns HTTP 409. List responses include a
bounded, batch-resolved `relation_display` map so clients render the target
table's `display_field_key`, never a UUID.

Each table obtains an explicit display identity when its first text/long-text
field is created. It is stored as `TableDefinition.display_field_key`.

Current selector loading is bounded to 100 target records. Search/autocomplete,
multi-relations and configurable deletion policies remain future work.
