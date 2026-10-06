# Test data: create, prove, change, clean up

Four small suites, each its own test, showing the ways a CRT test can handle its own data in Salesforce. The same
approach applies to any system with an API and a UI: build the data through the API, prove it on the screen and in
the database, and leave nothing behind.

All four run on **slockard** with the CRT variables `${client_idSlock}`, `${usernameSlock}` and `${private_keySlock}`.
Every value is generated with FakerLibrary, so the suites can run again and again without clashing.

| Suite | What it shows | Answers |
|---|---|---|
| `01-api-related-data-set.robot` | One Account, two Contacts, an Opportunity and a contact role, each created by API with the Id of the record it belongs to. Proved by query (counts, and the relationship itself) and on screen (the Account's related lists). Teardown deletes them, children first, and proves each is gone. | "The heavy engineering of preparing test data" |
| `02-ui-create-update-delete.robot` | A record made, changed and deleted through the UI, each step proved on screen and by query. The delete happens on the record's own page; the page is then reloaded and the record is shown to be gone. | Inline data, and proof that a delete really happened |
| `03-bulk-create-and-find.robot` | A batch of Leads created in one block (set `${batch_size}`), counted by query, and found in the "Today's Leads" list view by searching their shared company. Teardown deletes the batch. | Volume, and finding just-created data the way a person would |
| `04-baseline-and-restore.robot` | A test that must change data it cannot delete: it reads a BASELINE of the fields it will touch, changes them in the UI, and its teardown writes the baseline back and proves every field is restored. | "Data altered by the test, when a full teardown is not possible" |

**The shared pieces** live in `resources/data_handling.robot`:
- `Delete Created Records` is the teardown for suites 01 to 03. Each test keeps a list of what it created
  (`Append To List    ${created}    Account:${account_id}` after every `Create Record`). The teardown deletes newest
  first and queries each record to prove it is gone. It skips anything the test already deleted itself.
- `Restore Field Baseline` writes a dictionary of field values back to one record and queries to prove each field.

**Validating data from several sources** (the second question): each suite checks the same fact twice, once on the
screen and once with `QueryRecords`, and suite 01 also checks the relationship between records (the contact role
points at the right Contact and the right Account). In a real migration the same shape applies: query the target
system, compare each field against the value from the source system, and report the fields that differ.

**Keywords used:** QForce `Create Record`, `Update Record`, `Delete Record`, `QueryRecords`, `GetRecordIDFromUrl`,
`PickList`; QWeb `GoTo`, `TypeText`, `ClickText`, `VerifyText`, `VerifyNoText`, `UseModal`, `PressKey`.
Suites 02 and 04 import `resources/garzai_typetext_override.robot`, so `TypeText` clears a field and reads back what
landed. Stock `TypeText` appends to a field that already holds a value.
