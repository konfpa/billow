# Access is granted, never assumed

An Operator may do only what their Roles grant, and a User with no Role can
do nothing but sign in. Roles are Django Groups holding Django's model
permissions (`view`, `add` and `change` per model, plus `archive_customer`
and `archive_item`, each of which covers restoring as well), and only a
Superuser defines or grants them. Every view declares the permission it
requires, and a test walking the URLconf fails on any view that declares
none and is not on its short exempt list, so a view added later is refused
to everyone until someone decides who may use it.

## Considered Options

A `role` field on the User with permissions fixed in code was simpler to read,
but every new kind of Operator would have cost a release. Groups are already
on the User through `PermissionsMixin` and already on screen in the admin, and
leaving them unenforced was the bug: the admin offered a control that did
nothing.

Relying on each view to remember its check was rejected for the same reason
the setup gate is middleware — the release where one forgets is the one that
leaks.

## Consequences

Existing Users were not grandfathered. Before this, every User could do
everything; on the release that enforces permissions, every User who is not a
Superuser holds no Role and is locked out until a Superuser grants one. That
was chosen over a migration that quietly handed everyone full access, which
would have made the default "everything" for exactly the Users nobody had
thought about.

No Roles ship with billow. Which work belongs together is the Business's
decision, so the Superuser builds Roles in the admin.
