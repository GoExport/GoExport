import helpers
import moviepy
import numpy as np

class Editor:
    def __init__(self):
        # Video clips
        self.clips = []

    # Add a clip to the editor
    def add_clip(self, path: str, position: int, width: int = 1280, height: int = 720):
        if helpers.try_path(path) is False:
            raise FileNotFoundError(f"File not found: {path}")
        self.clips.insert(position, moviepy.VideoFileClip(path))

    # Trim a clip (you put in the clip id and it trims it to the start and end time)
    def trim(self, clip_id: int, start: int, end: int):
        self.clips[clip_id] = self.clips[clip_id].subclipped(start, end)

    # Get the length of a clip
    def get_clip_length(self, clip_id: int):
        return self.clips[clip_id].duration

    # Render the video (The clips is the order)
    def render(self, output: str):
        final_clip = moviepy.concatenate_videoclips(self.clips)
        final_clip.write_videofile(output)