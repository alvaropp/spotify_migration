#!/usr/bin/env python3
"""
Collects followed artists and top artists from Spotify.
"""
import json
import os
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Create data directory if it doesn't exist
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def load_config():
    """Load configuration from config.json"""
    with open("config.json", "r") as f:
        return json.load(f)

def get_spotify_client():
    """Initialize and return Spotify client with user authentication"""
    config = load_config()

    scope = "user-follow-read user-top-read"

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=config["spotify"]["client_id"],
        client_secret=config["spotify"]["client_secret"],
        redirect_uri=config["spotify"]["redirect_uri"],
        scope=scope,
        cache_path=".spotify_cache"
    ))

    return sp

def get_followed_artists(sp):
    """Get all artists the user follows"""
    print("Fetching followed artists...")
    artists = []

    results = sp.current_user_followed_artists(limit=50)
    artists.extend(results['artists']['items'])

    while results['artists']['next']:
        results = sp.next(results['artists'])
        artists.extend(results['artists']['items'])

    print(f"Found {len(artists)} followed artists")

    # Extract relevant information
    artist_data = []
    for artist in artists:
        artist_data.append({
            "name": artist["name"],
            "id": artist["id"],
            "genres": artist.get("genres", []),
            "popularity": artist.get("popularity", 0),
            "followers": artist.get("followers", {}).get("total", 0),
            "spotify_url": artist["external_urls"]["spotify"]
        })

    # Save to file
    output_file = DATA_DIR / "spotify_followed_artists.json"
    with open(output_file, "w") as f:
        json.dump(artist_data, f, indent=2)

    print(f"Saved followed artists to {output_file}")
    return artist_data

def get_top_artists(sp, time_ranges=["short_term", "medium_term", "long_term"]):
    """Get top artists the user has listened to"""
    print("Fetching top artists...")
    all_top_artists = {}

    for time_range in time_ranges:
        print(f"  Fetching {time_range} top artists...")
        results = sp.current_user_top_artists(limit=50, time_range=time_range)

        all_top_artists[time_range] = []
        for artist in results['items']:
            all_top_artists[time_range].append({
                "name": artist["name"],
                "id": artist["id"],
                "genres": artist.get("genres", []),
                "popularity": artist.get("popularity", 0),
                "followers": artist.get("followers", {}).get("total", 0),
                "spotify_url": artist["external_urls"]["spotify"]
            })

    # Save to file
    output_file = DATA_DIR / "spotify_top_artists.json"
    with open(output_file, "w") as f:
        json.dump(all_top_artists, f, indent=2)

    print(f"Saved top artists to {output_file}")
    return all_top_artists

def get_combined_artists():
    """Combine followed and top artists into a unique list"""
    followed_file = DATA_DIR / "spotify_followed_artists.json"
    top_file = DATA_DIR / "spotify_top_artists.json"

    if not followed_file.exists() or not top_file.exists():
        print("Error: Artist data files not found. Run collection first.")
        return []

    with open(followed_file, "r") as f:
        followed = json.load(f)

    with open(top_file, "r") as f:
        top_artists = json.load(f)

    # Combine all artists by ID to avoid duplicates
    artists_dict = {}

    # Add followed artists
    for artist in followed:
        artists_dict[artist["id"]] = {
            **artist,
            "source": ["followed"]
        }

    # Add top artists
    for time_range, artists in top_artists.items():
        for artist in artists:
            if artist["id"] in artists_dict:
                if time_range not in artists_dict[artist["id"]]["source"]:
                    artists_dict[artist["id"]]["source"].append(time_range)
            else:
                artists_dict[artist["id"]] = {
                    **artist,
                    "source": [time_range]
                }

    combined = list(artists_dict.values())

    # Save combined list
    output_file = DATA_DIR / "spotify_all_artists.json"
    with open(output_file, "w") as f:
        json.dump(combined, f, indent=2)

    print(f"\nTotal unique artists: {len(combined)}")
    print(f"Saved combined list to {output_file}")
    return combined

if __name__ == "__main__":
    try:
        sp = get_spotify_client()

        # Collect followed artists
        followed = get_followed_artists(sp)

        # Collect top artists
        top = get_top_artists(sp)

        # Create combined list
        combined = get_combined_artists()

        print("\n✓ Spotify data collection complete!")

    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure to:")
        print("1. Fill in your Spotify API credentials in config.json")
        print("2. Create a Spotify app at https://developer.spotify.com/dashboard")
        print("3. Add http://localhost:8888/callback to your app's redirect URIs")
