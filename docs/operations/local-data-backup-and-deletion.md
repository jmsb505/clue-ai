# Local data backup and deletion

Clue stores its SQLite database and CV files under `.data/` by default. The TypeSafe key is stored separately in the ignored `.env`; backups of `.data/` intentionally do not include that key. Re-enter the key on a replacement installation.

## Manual backup and restore

There is no automatic or cloud backup feature. For a manual backup at no recurring cost:

1. Stop the Clue server so the database is not being written.
2. Copy the complete `.data/` directory to an offline local destination of your choice. Encryption is optional for this single-user local setup; do not put the backup inside the repository or an unreviewed cloud-sync folder.
3. To restore, stop Clue, preserve the current `.data/` under another name, copy the backup into the configured data location, and start Clue to check the profile and CV.

The Conda `gen` test suite copies a database and synthetic CV from a stopped app into a backup and restore directory, then verifies both can be read. It does not verify encryption settings, a particular external drive, cloud-sync behavior, or Windows account permissions. On 2026-09-30 the owner waived device-encryption verification for the local `.data/` directory and backups.

## Deletion scope

The Settings action removes the current profile, CV files, local listings, search history, saved/hidden state, usage ledger, and user-added sources from the active `.data/` directory. It also clears Jev consent and resets tracked-company choices. The built-in company directory and connector definitions remain, but all catalog entries return to untracked. It does not remove `.data/` copies the owner made elsewhere, backups held by the operating system, or data already processed by TypeSafe. Delete manual backups separately when they are no longer wanted. TypeSafe's public agreement allows some customer data to remain in its standard backups under confidentiality terms; the user's account-specific deletion behavior is unknown.

The owner chose not to require device-encryption verification for local data. File protection follows the computer's existing account and storage settings, which this project does not inspect. Keep personal data out of Git; `.env` and `.data/` are ignored.
