from recap import Recorder, RecordingConfig

def test_enhanced_capture():
    output = "test_output.mp4"
    window = "FlashThemes - GoExport Update Video - Watch Animation - Chromium"

    config = RecordingConfig(
        output=output,
        window_title=window,
        overwrite=True,
        crop_position="top-left",
        crop_width=1280,
        crop_height=720,
        fps=60,
    )
    recorder = Recorder(config)

    recorder.start()
    print("Recording started.")
    recorder.wait(timeout=10)
    recorder.stop()
    print("Recording stopped.")

test_enhanced_capture()