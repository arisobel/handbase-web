# Domain Model

> **Status:** Active | **Last updated:** 2026-09-18

## Implemented
- Workspace
- TableDefinition
- FieldDefinition
- Record
- ViewDefinition (model only; no endpoints yet)
- User
- WorkspaceMembership (role: OWNER / ADMIN / EDITOR / VIEWER)
- RefreshToken

## Planned
- Invitation
- Role / Permission as first-class editable entities
  (today roles are a fixed enum mapped to capabilities in code)
- RelationDefinition
- Activity / AuditEvent
- Task / Follow-up
- Attachment

`Student`, `Family` and `Teacher` are user-defined data models, not core classes.
