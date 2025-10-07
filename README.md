# Spotify to Tidal Migration

Tools to migrate your Spotify data to Tidal.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a Spotify app:
   - Go to https://developer.spotify.com/dashboard
   - Create a new app
   - Add `http://localhost:8888/callback` to Redirect URIs
   - Copy your Client ID and Client Secret

3. Update `config.json` with your Spotify credentials

## Usage

### Authenticate with Tidal

First, authenticate with Tidal:

```bash
python tidal_auth.py
```

This will open a browser for OAuth login and save your session.

### Artist Migration

#### Step 1: Collect Spotify Artists

Run the collector script to get your followed artists and top listened artists:

```bash
python spotify_collector.py
```

This will:
- Fetch all artists you follow
- Fetch your top artists (recent, medium-term, long-term)
- Save data to `data/spotify_followed_artists.json`, `data/spotify_top_artists.json`, and `data/spotify_all_artists.json`

#### Step 2: Check Tidal Availability

Check which artists are available on Tidal:

```bash
python tidal_checker.py
```

This will:
- Search for each artist on Tidal
- Save results to `data/tidal_availability.json`
- Generate a report at `data/migration_report.md`

### Playlist Migration

#### Step 1: Export Spotify Playlists

Export your personally created playlists:

```bash
python playlist_exporter.py
```

This will:
- Fetch all playlists you own (not playlists you follow)
- Extract all track information including ISRC codes
- Save to `data/spotify_playlists.json`

#### Step 2: Migrate to Tidal

Test the migration first (dry run):

```bash
python playlist_migrator.py --dry-run
```

When ready, migrate for real:

```bash
python playlist_migrator.py
```

This will:
- Search for each track on Tidal (using ISRC when available)
- Create playlists on Tidal with the same names and descriptions
- Add all found tracks to the playlists
- Generate a detailed report at `data/playlist_migration_report.md`

## Output Files

### Artists
- `data/spotify_followed_artists.json` - Artists you follow on Spotify
- `data/spotify_top_artists.json` - Your top listened artists
- `data/spotify_all_artists.json` - Combined unique list
- `data/tidal_availability.json` - Complete results with Tidal matches
- `data/migration_report.md` - Human-readable artist migration report

### Playlists
- `data/spotify_playlists.json` - Your Spotify playlists with full track info
- `data/playlist_migration_results.json` - Detailed migration results
- `data/playlist_migration_report.md` - Human-readable playlist migration report
