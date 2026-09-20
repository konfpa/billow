# A custom user model, identified by email

billow replaces `django.contrib.auth.models.User` with its own model, built on
`AbstractBaseUser` and `PermissionsMixin`, whose `USERNAME_FIELD` is a unique
case-insensitive `email` and which has no `username` at all. A User is a person
who logs in; the customers billow invoices are a separate model with no
credentials, so the two never share a table.

## Considered Options

Subclassing `AbstractUser` and setting `username = None` was the cheaper route,
but it inherits a shape we would then spend the model arguing with: a username
field to neuter, `first_name`/`last_name` we do not want (a single `name` is
stored instead), and validators and `Meta` that come along uninvited. Declaring
roughly thirty lines of fields we chose outright is clearer, and this table is
permanent.

## Consequences

Swapping the user model is only free before the first migration exists, which
is why it lands ahead of any other model. A User is never deleted, only
deactivated, so every later foreign key naming a User as an actor uses
`on_delete=PROTECT`.
