import argparse

class Parameters:
    def __init__(self):
        parser = argparse.ArgumentParser(description="Automate the process of exporting videos for GoExport")
        parser.add_argument("-ni", "--no-input", help="Skip all user input", action="store_true", dest="no_input")
        parser.add_argument("-v", "--verbose", help="Enable verbose output", action="store_true", dest="verbose")
        parser.add_argument("-s", "--service", help="Set the service to use", dest="service")
        parser.add_argument("-r", "--resolution", help="Set the resolution to use", dest="resolution")
        parser.add_argument("-asr", "--aspect_ratio", help="Set the aspect ratio", dest="aspect_ratio")
        parser.add_argument("-oi", "--owner-id", help="Set the owner ID", dest="owner_id")
        parser.add_argument("-mi", "--movie-id", help="Set the movie ID", dest="movie_id")
        parser.add_argument("-ae", "--auto-edit", help="Enable auto editing", action="store_true", dest="auto_edit")

        # Quality parameters
        parser.add_argument("-f", "--framerate", help="Set the framerate of the output", dest="framerate", type=int, default=24)
        parser.add_argument("-b", "--bitrate", help="Set the bitrate of the output", dest="bitrate", type=int, default=5000)
        parser.add_argument("-c", "--codec", help="Set the codec to use for video encoding", dest="codec", default="libx264")
        parser.add_argument("-a", "--audio_bitrate", help="Set the audio bitrate", dest="audio_bitrate", type=int, default=128)
        parser.add_argument("-p", "--preset", help="Set the encoding preset", dest="preset", default="ultrafast")
        parser.add_argument("-crf", "--constant_rate_factor", help="Set the CRF value for video quality", dest="crf", type=int, default=23)
        parser.add_argument("-pix_fmt", "--pixel_format", help="Set the pixel format for video encoding", dest="pix_fmt", default="yuv420p")
        parser.add_argument("-ac", "--audio_codec", help="Set the audio codec to use", dest="audio_codec", default="aac")
        parser.add_argument("-ar", "--audio_sample_rate", help="Set the audio sample rate", dest="audio_sample_rate", type=int, default=44100)

        args = parser.parse_args()
        for key, value in vars(args).items():
            setattr(self, key, value)