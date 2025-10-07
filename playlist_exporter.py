#!/usr/bin/env python3
"""
Export personally created playlists from Spotify.
"""
import json
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyOAuth

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def load_config():
    """Load configuration from config.json"""
    with open("config.json", "r") as f:
        return json.load(f)

def get_spotify_client():
    """Initialize and return Spotify client with user authentication"""
    config = load_config()

    scope = "playlist-read-private playlist-read-collaborative"

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=config["spotify"]["client_id"],
        client_secret=config["spotify"]["client_secret"],
        redirect_uri=config["spotify"]["redirect_uri"],
        scope=scope,
        cache_path=".spotify_cache"
    ))

    return sp

def get_user_playlists(sp):
    """Get all playlists owned by the current user"""
    print("Fetching your playlists...\n")

    # Get current user info
    current_user = sp.current_user()
    user_id = current_user['id']
    print(f"Logged in as: {current_user['display_name']} ({user_id})\n")

    playlists = []
    results = sp.current_user_playlists(limit=50)

    while results:
        for playlist in results['items']:
            # Only include playlists owned by the current user
            if playlist['owner']['id'] == user_id:
                playlists.append(playlist)
                print(f"  Found: {playlist['name']} ({playlist['tracks']['total']} tracks)")

        if results['next']:
            results = sp.next(results)
        else:
            break

    print(f"\nTotal personally created playlists: {len(playlists)}")
    return playlists, user_id

def get_playlist_tracks(sp, playlist_id):
    """Get all tracks from a playlist"""
    tracks = []
    results = sp.playlist_tracks(playlist_id, limit=100)

    while results:
        for item in results['items']:
            if item['track'] is not None:  # Skip local files or removed tracks
                track = item['track']
                tracks.append({
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'album': track['album']['name'],
                    'uri': track['uri'],
                    'id': track['id'],
                    'isrc': track.get('external_ids', {}).get('isrc'),  # International Standard Recording Code
                    'duration_ms': track['duration_ms']
                })

        if results['next']:
            results = sp.next(results)
        else:
            break

    return tracks

def export_playlists():
    """Export all personally created playlists with their tracks"""
    sp = get_spotify_client()

    playlists, user_id = get_user_playlists(sp)

    if not playlists:
        print("No personally created playlists found.")
        return

    print("\nExporting playlist details...\n")

    exported_playlists = []

    for i, playlist in enumerate(playlists, 1):
        print(f"[{i}/{len(playlists)}] Exporting: {playlist['name']}")

        tracks = get_playlist_tracks(sp, playlist['id'])

        playlist_data = {
            'spotify_id': playlist['id'],
            'name': playlist['name'],
            'description': playlist.get('description', ''),
            'public': playlist['public'],
            'collaborative': playlist['collaborative'],
            'track_count': len(tracks),
            'spotify_url': playlist['external_urls']['spotify'],
            'tracks': tracks
        }

        exported_playlists.append(playlist_data)
        print(f"    Exported {len(tracks)} tracks")

    # Save to file
    output_file = DATA_DIR / "spotify_playlists.json"
    with open(output_file, "w") as f:
        json.dump(exported_playlists, f, indent=2)

    print(f"\n✓ Exported {len(exported_playlists)} playlists to {output_file}")

    # Print summary
    total_tracks = sum(p['track_count'] for p in exported_playlists)
    print(f"\nSummary:")
    print(f"  Total playlists: {len(exported_playlists)}")
    print(f"  Total tracks: {total_tracks}")

    return exported_playlists

if __name__ == "__main__":
    try:
        playlists = export_playlists()
    except Exception as e:
        print(f"Error: {e}")
