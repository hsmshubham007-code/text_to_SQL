# Chinook Database Schema

## 1. Overview

Chinook represents a digital music store. It contains information about customers, employees, invoices, music tracks, artists, albums, genres, media types, and playlists.

- Database engine: SQLite
- Database file: `data/chinook.db`
- Number of tables: 11
- Total rows: 15,607
- Purpose: Text-to-SQL development and evaluation

## 2. Tables and Row Counts

| Table | Rows | Purpose |
|---|---:|---|
| Artist | 275 | Music artists |
| Album | 347 | Albums and their artists |
| Customer | 59 | Customer details |
| Employee | 8 | Employees and reporting structure |
| Genre | 25 | Music genres |
| Invoice | 412 | Customer invoices and billing totals |
| InvoiceLine | 2,240 | Tracks purchased on invoices |
| MediaType | 5 | Audio media formats |
| Playlist | 18 | Music playlists |
| PlaylistTrack | 8,715 | Tracks included in playlists |
| Track | 3,503 | Music catalog and track prices |

## 3. Primary Keys

- Artist: `ArtistId`
- Album: `AlbumId`
- Customer: `CustomerId`
- Employee: `EmployeeId`
- Genre: `GenreId`
- Invoice: `InvoiceId`
- InvoiceLine: `InvoiceLineId`
- MediaType: `MediaTypeId`
- Playlist: `PlaylistId`
- Track: `TrackId`
- PlaylistTrack: composite key (`PlaylistId`, `TrackId`)

## 4. Relationships

- `Album.ArtistId` references `Artist.ArtistId`.
- `Customer.SupportRepId` references `Employee.EmployeeId`.
- `Employee.ReportsTo` references `Employee.EmployeeId`.
- `Invoice.CustomerId` references `Customer.CustomerId`.
- `InvoiceLine.InvoiceId` references `Invoice.InvoiceId`.
- `InvoiceLine.TrackId` references `Track.TrackId`.
- `Track.AlbumId` references `Album.AlbumId`.
- `Track.GenreId` references `Genre.GenreId`.
- `Track.MediaTypeId` references `MediaType.MediaTypeId`.
- `PlaylistTrack.PlaylistId` references `Playlist.PlaylistId`.
- `PlaylistTrack.TrackId` references `Track.TrackId`.

## 5. Important Query Patterns

### Customer spending

Join `Customer` to `Invoice` using `CustomerId`. Use `SUM(Invoice.Total)` to calculate invoice-based spending.

### Tracks sold

Join `InvoiceLine` to `Track` using `TrackId`. Use `SUM(InvoiceLine.Quantity)` to count units sold.

### Sales by artist

Join `Artist` to `Album`, `Album` to `Track`, and `Track` to `InvoiceLine`. Aggregate the line-item revenue using `SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity)`.

### Sales by genre

Join `Genre` to `Track` and then to `InvoiceLine`. Group results by genre.

### Customers by support representative

Join `Customer.SupportRepId` to `Employee.EmployeeId`.

### Playlist contents

Join `Playlist` to `PlaylistTrack`, then to `Track`.

## 6. Data Limitations

The database describes a music store, not a general business.

It does not contain dedicated records for:

- Product inventory levels or warehouse stock.
- Customer support tickets and resolution times.
- Customer satisfaction survey scores.
- Marketing campaign performance.
- Customer demographics such as age.

Questions requiring these facts cannot be answered reliably from the available schema.

## 7. Safety Boundary

The application must use read-only database access and validate generated SQL before execution.

Only approved read queries should be allowed. Data-changing statements, schema modifications, and other unsafe operations must be rejected.

The agent must not invent information that is absent from the database.
