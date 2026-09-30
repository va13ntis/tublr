#!/usr/bin/env python3
"""
Test script to verify pytubefix 11.2.0 works correctly
"""
import sys
from pytubefix import YouTube

def test_pytubefix_basic():
    """Test basic pytubefix functionality"""
    print("Testing pytubefix 11.2.0...")
    print("-" * 50)
    
    # Test video URL (Rick Astley - Never Gonna Give You Up)
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        print(f"Fetching video info for: {video_url}")
        yt = YouTube(video_url)
        
        # Test basic metadata
        print(f"✓ Title: {yt.title}")
        print(f"✓ Author: {yt.author}")
        print(f"✓ Length: {yt.length} seconds")
        print(f"✓ Views: {yt.views:,}")
        
        # Test streams
        print(f"\n✓ Total streams available: {len(yt.streams)}")
        
        # Test video streams
        video_streams = yt.streams.filter(type="video")
        print(f"✓ Video streams: {len(video_streams)}")
        
        # Test audio streams
        audio_streams = yt.streams.filter(type="audio")
        print(f"✓ Audio streams: {len(audio_streams)}")
        
        # Test getting highest resolution
        highest_res = yt.streams.get_highest_resolution()
        if highest_res:
            print(f"✓ Highest resolution: {highest_res.resolution}")
        
        # Test getting audio only
        audio_only = yt.streams.get_audio_only()
        if audio_only:
            print(f"✓ Audio only bitrate: {audio_only.abr}")
        
        print("\n" + "=" * 50)
        print("✓ All pytubefix tests PASSED!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n✗ Test FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pytubefix_basic()
    sys.exit(0 if success else 1)
