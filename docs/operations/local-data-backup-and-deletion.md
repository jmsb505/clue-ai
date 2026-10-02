# Local data backup and deletion

Clue stores its SQLite database and CV files under `.data/` by default. The TypeSafe key is stored separately in the ignored `.env`; backups of `.data/` intentionally do not include that key. Re-enter the key on a replacement installation.

## Manual backup and restore

There is no cloud backup feature. A search reset creates a local database snapshot; for a complete manual backup including CV files at no recurring cost:

1. Stop the Clue server so the database is not being written.
2. Copy the complete `.data/` directory to an offline local destination of your choice. Encryption is optional for this single-user local setup; do not put the backup inside the repository or an unreviewed cloud-sync folder.
3. To restore, stop Clue, preserve the current `.data/` under another name, copy the backup into the configured data location, and start Clue to check the profile and CV.

The Conda `gen` test suite copies a database and synthetic CV from a stopped app into a backup and restore directory, then verifies both can be read. It does not verify encryption settings, a particular external drive, cloud-sync behavior, or Windows account permissions. On 2026-09-30 the owner waived device-encryption verification for the local `.data/` directory and backups.

## Repair saved matching decisions

The October 3 correction recovers retained Jev choices previously downgraded by a local confidence cutoff and enforces explicit work-region restrictions. To repair completed five-check results without another crawl or TypeSafe charge:

```powershell
.\scripts\clue.ps1 stop
conda run -n gen python -m clue_ai.repair_matching
.\scripts\clue.ps1 start
```

The repair creates `.data/backups/before-matching-repair-*.sqlite3`, preserves raw model choices and candidate fit scores, and updates derived filters/counts with an explicit correction notice. Profile, CV, source timers and spend remain. Repeating the repair does not reinterpret already corrected checks. Active searches must be stopped; invalid retained answers abort and roll back the transaction. Restore the backup with Clue stopped using the database restore precautions below.

## Deletion scope

### Start a fresh job search

Run `.\scripts\clue.ps1 reset` from the repository. It stops the server and its crawler process tree, creates a SQLite snapshot under ignored `.data/backups/before-reset-*.sqlite3`, then clears indexed listings, saved/hidden jobs, saved searches/results, per-query refresh records and source/company refresh timestamps in one transaction. Source configurations, enabled choices and tracked-company selections remain. The CV, profile, application tracker with known posting links, Jev consent, `.env` and Jev spend ledger remain; deleting a search does not refund an API charge. Old ledger entries lose their search reference but still count toward the rolling limit.

The app stays stopped after reset. Use `.\scripts\clue.ps1 start` for the next search. Every enabled source starts without a refresh cooldown. The reset refuses unfinished searches; the stop helper first marks interrupted work as stopped. If a reset fails during mutation, the transaction rolls back. Repeating it is safe and creates another local snapshot.

To undo a reset, stop Clue, preserve the current database, and replace it with the `before-reset` snapshot. Ensure no old `clue.sqlite3-wal` or `clue.sqlite3-shm` files from the replaced database remain before opening the snapshot. This snapshot includes the saved profile but not CV files or `.env`, which the reset does not change. These local backups retain old search data until you delete them separately.

### Remove all personal data

The full personal-data deletion control also deletes application records and their links. Undo applied on the Applied roles page removes one record; it leaves bookmarks/hidden state unchanged. Clearing only search history or using search reset preserves the application tracker. Database backups retain earlier records until separately removed.

The Settings action removes the current profile, CV files, local listings, search history, saved/hidden state, usage ledger, and user-added sources from the active `.data/` directory. It also clears Jev consent and resets tracked-company choices. The built-in company directory and connector definitions remain, but all catalog entries return to untracked. It does not remove `.data/` copies the owner made elsewhere, backups held by the operating system, or data already processed by TypeSafe. Delete manual backups separately when they are no longer wanted. TypeSafe's public agreement allows some customer data to remain in its standard backups under confidentiality terms; the user's account-specific deletion behavior is unknown.

The owner chose not to require device-encryption verification for local data. File protection follows the computer's existing account and storage settings, which this project does not inspect. Keep personal data out of Git; `.env` and `.data/` are ignored.
