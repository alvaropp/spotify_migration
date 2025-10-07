#!/usr/bin/env python3
"""
Checks if Spotify artists are available on Tidal and generates a report.
"""
import json
import time
from pathlib import Path
import tidalapi
from tidal_auth import load_tidal_session

DATA_DIR = Path("data")

def search_artist_on_tidal(artist_name, tidal_session):
    """
    Search for an artist on Tidal using the authenticated API.
    """
    try:
        results = tidal_session.search(artist_name, models=[tidalapi.artist.Artist], limit=5)

        if results.get('artists') and len(results['artists']) > 0:
            # Get the first match
            top_match = results['artists'][0]
            return {
                "found": True,
                "tidal_id": top_match.id,
                "tidal_name": top_match.name,
                "tidal_url": f"https://listen.tidal.com/artist/{top_match.id}"
            }

        return {"found": False}

    except Exception as e:
        print(f"  Error searching for {artist_name}: {e}")
        return {"found": False, "error": str(e)}

def check_artists_on_tidal():
    """Check all Spotify artists on Tidal"""
    input_file = DATA_DIR / "spotify_all_artists.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run spotify_collector.py first.")
        return

    with open(input_file, "r") as f:
        artists = json.load(f)

    print(f"Checking {len(artists)} artists on Tidal...\n")

    # Load Tidal session
    tidal_session = load_tidal_session()
    if not tidal_session:
        print("Failed to authenticate with Tidal")
        return

    results = []

    for i, artist in enumerate(artists, 1):
        print(f"[{i}/{len(artists)}] Checking: {artist['name']}")

        tidal_result = search_artist_on_tidal(artist['name'], tidal_session)

        result = {
            **artist,
            "tidal_found": tidal_result.get("found", False),
            "tidal_id": tidal_result.get("tidal_id"),
            "tidal_name": tidal_result.get("tidal_name"),
            "tidal_url": tidal_result.get("tidal_url"),
        }

        if tidal_result.get("error"):
            result["tidal_error"] = tidal_result["error"]

        results.append(result)

        # Be respectful with rate limiting
        time.sleep(0.3)

    # Save results
    output_file = DATA_DIR / "tidal_availability.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Saved results to {output_file}")
    return results

def generate_report():
    """Generate a human-readable report"""
    input_file = DATA_DIR / "tidal_availability.json"

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run check first.")
        return

    with open(input_file, "r") as f:
        results = json.load(f)

    found_count = sum(1 for r in results if r["tidal_found"])
    not_found_count = len(results) - found_count

    # Generate markdown report
    report_lines = [
        "# Spotify to Tidal Artist Migration Report",
        "",
        f"**Total Artists:** {len(results)}",
        f"**Found on Tidal:** {found_count} ({found_count/len(results)*100:.1f}%)",
        f"**Not Found:** {not_found_count} ({not_found_count/len(results)*100:.1f}%)",
        "",
        "---",
        "",
        "## Artists Found on Tidal",
        ""
    ]

    for result in results:
        if result["tidal_found"]:
            source_str = ", ".join(result["source"])
            report_lines.append(f"- **{result['name']}** ({source_str})")
            report_lines.append(f"  - Spotify: {result['spotify_url']}")
            report_lines.append(f"  - Tidal: {result['tidal_url']}")
            report_lines.append("")

    report_lines.extend([
        "---",
        "",
        "## Artists NOT Found on Tidal",
        ""
    ])

    for result in results:
        if not result["tidal_found"]:
            source_str = ", ".join(result["source"])
            report_lines.append(f"- **{result['name']}** ({source_str})")
            report_lines.append(f"  - Spotify: {result['spotify_url']}")
            report_lines.append("")

    # Save report
    report_file = DATA_DIR / "migration_report.md"
    with open(report_file, "w") as f:
        f.write("\n".join(report_lines))

    print(f"\n✓ Generated report: {report_file}")

    # Print summary to console
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Artists: {len(results)}")
    print(f"Found on Tidal: {found_count} ({found_count/len(results)*100:.1f}%)")
    print(f"Not Found: {not_found_count} ({not_found_count/len(results)*100:.1f}%)")
    print("="*50)

if __name__ == "__main__":
    results = check_artists_on_tidal()
    if results:
        generate_report()
