import argparse

class Parameters:
    def __init__(self):
        parser = argparse.ArgumentParser(description="Automate the process of exporting videos for GoExport")
        parser.add_argument("-ni", "--no-input", help="Skip all user input", action="store_true", dest="no_input")
        parser.add_argument("-s", "--service", help="Set the service to use", dest="service")
        parser.add_argument("-r", "--resolution", help="Set the resolution to use", dest="resolution")
        parser.add_argument("-oi", "--owner-id", help="Set the owner ID", dest="owner_id")
        parser.add_argument("-mi", "--movie-id", help="Set the movie ID", dest="movie_id")
        parser.add_argument("-ae", "--auto-edit", help="Enable auto editing", action="store_true", dest="auto_edit")
        args = parser.parse_args()
        for key, value in vars(args).items():
            setattr(self, key, value)