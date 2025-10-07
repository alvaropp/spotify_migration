#!/usr/bin/env python3
"""
Migrate Spotify playlists to Tidal.
"""
import json
import time
from pathlib import Path
import tidalapi
from tidal_auth import load_tidal_session

DATA_DIR = Path("data")

def search_track_on_tidal(track_info, tidal_session):
    """
    Search for a track on Tidal using various search strategies.
    Returns the best match or None.
    """
    # Strategy 1: Search by ISRC (most reliable)
    if track_info.get('isrc'):
        try:
            results = tidal_session.search(track_info['isrc'], models=[tidalapi.media.Track], limit=5)
            if results.get('tracks') and len(results['tracks']) > 0:
                for track in results['tracks']:
                    if track.isrc == track_info['isrc']:
                        return track
        except Exception as e:
            pass  # Fall through to next strategy

    # Strategy 2: Search by "Artist - Track Name"
    artists_str = ", ".join(track_info['artists'][:2])  # Use first 2 artists
    query = f"{artists_str} {track_info['name']}"

    try:
        results = tidal_session.search(query, models=[tidalapi.media.Track], limit=10)

        if results.get('tracks') and len(results['tracks']) > 0:
            # Find best match by comparing artist and track name
            track_name_lower = track_info['name'].lower()
            track_artists_lower = [a.lower() for a in track_info['artists']]

            for tidal_track in results['tracks']:
                tidal_name_lower = tidal_track.name.lower()
                tidal_artist_lower = tidal_track.artist.name.lower()

                # Check if names match closely
                if track_name_lower in tidal_name_lower or tidal_name_lower in track_name_lower:
                    # Check if at least one artist matches
                    if any(artist in tidal_artist_lower or tidal_artist_lower in artist
                           for artist in track_artists_lower):
                        return tidal_track

            # If no good match, return the first result
            return results['tracks'][0]

    except Exception as e:
        print(f"    Error searching: {e}")

    return None

def migrate_playlists(dry_run=False):
    """
    Migrate Spotify playlists to Tidal.

    Args:
        dry_run: If True, only search for tracks but don't create playlists
    """
    input_file = DATA_DIR / "spotify_playlists.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run playlist_exporter.py first.")
        return

    with open(input_file, "r") as f:
        playlists = json.load(f)

    print(f"Migrating {len(playlists)} playlists to Tidal...\n")

    # Load Tidal session
    tidal_session = load_tidal_session()
    if not tidal_session:
        print("Failed to authenticate with Tidal")
        return

    migration_results = []

    for i, playlist in enumerate(playlists, 1):
        print(f"\n[{i}/{len(playlists)}] Processing: {playlist['name']}")
        print(f"  Tracks: {playlist['track_count']}")

        track_results = []
        found_count = 0

        print(f"  Searching for tracks on Tidal...")

        for j, track in enumerate(playlist['tracks'], 1):
            track_str = f"{', '.join(track['artists'])} - {track['name']}"

            if j % 10 == 0:
                print(f"    Progress: {j}/{len(playlist['tracks'])}")

            tidal_track = search_track_on_tidal(track, tidal_session)

            if tidal_track:
                found_count += 1
                track_results.append({
                    'spotify_track': track,
                    'tidal_found': True,
                    'tidal_id': tidal_track.id,
                    'tidal_name': tidal_track.name,
                    'tidal_artist': tidal_track.artist.name,
                    'tidal_album': tidal_track.album.name if tidal_track.album else None
                })
            else:
                track_results.append({
                    'spotify_track': track,
                    'tidal_found': False
                })

            # Rate limiting
            time.sleep(0.2)

        if len(playlist['tracks']) > 0:
            print(f"  Found {found_count}/{len(playlist['tracks'])} tracks on Tidal ({found_count/len(playlist['tracks'])*100:.1f}%)")
        else:
            print(f"  Playlist is empty")

        # Create playlist on Tidal (if not dry run)
        tidal_playlist_id = None
        tidal_playlist_url = None

        if not dry_run:
            try:
                print(f"  Creating playlist on Tidal...")

                # Create the playlist
                tidal_playlist = tidal_session.user.create_playlist(
                    playlist['name'],
                    playlist.get('description', '')
                )

                tidal_playlist_id = tidal_playlist.id
                tidal_playlist_url = f"https://listen.tidal.com/playlist/{tidal_playlist_id}"

                # Add tracks to playlist
                tracks_to_add = [tr['tidal_id'] for tr in track_results if tr['tidal_found']]

                if tracks_to_add:
                    # Tidal has a limit on how many tracks can be added at once
                    batch_size = 100
                    for batch_start in range(0, len(tracks_to_add), batch_size):
                        batch = tracks_to_add[batch_start:batch_start + batch_size]
                        tidal_playlist.add(batch)
                        time.sleep(0.5)

                print(f"  ✓ Created playlist: {tidal_playlist_url}")

            except Exception as e:
                print(f"  ✗ Error creating playlist: {e}")

        migration_results.append({
            'spotify_playlist': {
                'name': playlist['name'],
                'description': playlist['description'],
                'track_count': playlist['track_count'],
                'spotify_url': playlist['spotify_url']
            },
            'tidal_playlist_id': tidal_playlist_id,
            'tidal_playlist_url': tidal_playlist_url,
            'tracks_found': found_count,
            'tracks_total': len(playlist['tracks']),
            'match_rate': found_count / len(playlist['tracks']) if len(playlist['tracks']) > 0 else 0,
            'track_results': track_results
        })

    # Save results
    output_file = DATA_DIR / "playlist_migration_results.json"
    with open(output_file, "w") as f:
        json.dump(migration_results, f, indent=2)

    print(f"\n✓ Saved migration results to {output_file}")
    return migration_results

def generate_playlist_report():
    """Generate a human-readable report for playlist migration"""
    input_file = DATA_DIR / "playlist_migration_results.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run migration first.")
        return

    with open(input_file, "r") as f:
        results = json.load(f)

    total_playlists = len(results)
    total_tracks = sum(r['tracks_total'] for r in results)
    total_found = sum(r['tracks_found'] for r in results)
    overall_match_rate = total_found / total_tracks if total_tracks > 0 else 0

    # Generate markdown report
    report_lines = [
        "# Spotify to Tidal Playlist Migration Report",
        "",
        f"**Total Playlists:** {total_playlists}",
        f"**Total Tracks:** {total_tracks}",
        f"**Tracks Found on Tidal:** {total_found} ({overall_match_rate*100:.1f}%)",
        f"**Tracks Not Found:** {total_tracks - total_found}",
        "",
        "---",
        "",
        "## Playlists",
        ""
    ]

    for result in results:
        playlist = result['spotify_playlist']
        report_lines.append(f"### {playlist['name']}")
        report_lines.append("")
        report_lines.append(f"**Tracks:** {result['tracks_found']}/{result['tracks_total']} found ({result['match_rate']*100:.1f}%)")
        report_lines.append("")
        report_lines.append(f"- Spotify: {playlist['spotify_url']}")

        if result.get('tidal_playlist_url'):
            report_lines.append(f"- Tidal: {result['tidal_playlist_url']}")
        else:
            report_lines.append(f"- Tidal: Not created (dry run)")

        report_lines.append("")

        if result['spotify_playlist'].get('description'):
            report_lines.append(f"*{result['spotify_playlist']['description']}*")
            report_lines.append("")

        # List tracks not found
        not_found = [tr for tr in result['track_results'] if not tr['tidal_found']]
        if not_found:
            report_lines.append(f"**Tracks not found on Tidal ({len(not_found)}):**")
            report_lines.append("")
            for tr in not_found[:20]:  # Limit to first 20
                track = tr['spotify_track']
                artists = ", ".join(track['artists'])
                report_lines.append(f"- {artists} - {track['name']}")

            if len(not_found) > 20:
                report_lines.append(f"- *(and {len(not_found) - 20} more)*")

            report_lines.append("")

        report_lines.append("---")
        report_lines.append("")

    # Save report
    report_file = DATA_DIR / "playlist_migration_report.md"
    with open(report_file, "w") as f:
        f.write("\n".join(report_lines))

    print(f"\n✓ Generated report: {report_file}")

    # Print summary to console
    print("\n" + "="*50)
    print("PLAYLIST MIGRATION SUMMARY")
    print("="*50)
    print(f"Total Playlists: {total_playlists}")
    print(f"Total Tracks: {total_tracks}")
    print(f"Tracks Found: {total_found} ({overall_match_rate*100:.1f}%)")
    print(f"Tracks Not Found: {total_tracks - total_found}")
    print("="*50)

if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("Running in DRY RUN mode - will not create playlists\n")

    results = migrate_playlists(dry_run=dry_run)
    if results:
        generate_playlist_report()
