#!/usr/bin/env python3
import scap
import sys

def main():
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    else:
        output_path = "capture.mp4"

    # Check if the platform is supported
    if not scap.is_supported():
        print("❌ Platform not supported")
        return

    # Check if we have permission to capture screen
    if not scap.has_permission():
        print("❌ Permission not granted. Requesting permission...")
        if not scap.request_permission():
            print("❌ Permission denied")
            return

    # Create Options
    options = scap.CaptureOptions(
        fps=24,
        target=None,
        show_cursor=False,
        show_highlight=False,
    )

    # Create Capturer
    capturer = scap.Capturer(options)
    
    # Start recording
    print(f"Recording to {output_path}...")
    capturer.start_capture()
    
    try:
        # Keep recording until interrupted
        input("Press Enter to stop recording...\n")
    except KeyboardInterrupt:
        print("\nStopping recording...")
    finally:
        capturer.stop_capture()
        print("Recording saved.")

if __name__ == "__main__":
    main()
