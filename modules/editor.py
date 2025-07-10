import helpers
import os

class Editor:
    """
    The following is the new video editing module for GoExport.
    It will not make use of MoviePy, but will instead use FFmpeg directly
    to manipulate video clips. This is to ensure better performance and
    compatibility across different systems.
    The module will allow for adding clips, trimming them, and rendering.
    """
    def __init__(self):
        # List of video clip locations
        self.clips = []
    
    def get_clip_length(self, clip_id: int):
        """
        Get the length of a video clip.
        :param clip_id: ID of the clip to get the length of.
        :raises IndexError: If the clip ID is out of range.
        """
        if clip_id < 0 or clip_id >= len(self.clips):
            raise IndexError(f"Clip ID {clip_id} is out of range.")
        
        try:
            output = helpers.try_command(
                helpers.get_path(None, helpers.get_config("PATH_FFPROBE_WINDOWS")),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                self.clips[clip_id],
                return_output=True
            )
            return float(output)
        except Exception as e:
            raise RuntimeError(f"Error getting length of clip {clip_id}: {e}")
    
    def add_clip(self, path: str, position: int = -1):
        """
        Add a video clip to the editor.
        :param path: Path to the video file.
        :param position: Position to insert the clip at (default: -1, which appends to the end).
        :raises FileNotFoundError: If the file does not exist.
        """
        if not helpers.try_path(path):
            raise FileNotFoundError(f"File not found: {path}")
        if position == -1:
            self.clips.append(path)
        else:
            self.clips.insert(position, path)

        print(f"Clip added at position {position}: {path}")
        print(f"Current clips: {self.clips}")
        
    def trim(self, clip_id: int, start: int, end: int):
        """
        Trim a clip to the specified start and end times.
        :param clip_id: ID of the clip to trim.
        :param start: Start time in seconds.
        :param end: End time in seconds.
        :raises IndexError: If the clip ID is out of range.
        """
        if clip_id < 0 or clip_id >= len(self.clips):
            raise IndexError(f"Clip ID {clip_id} is out of range.")
        
        if helpers.os_is_windows():
            try:
                trimmed_path = self.clips[clip_id].replace(".mp4", f"_trimmed_{start}_{end}.mp4")
                helpers.try_command(
                    helpers.get_path(None, helpers.get_config("PATH_FFMPEG_WINDOWS")),
                    "-ss", str(start),
                    "-i", self.clips[clip_id],
                    "-c", "copy",
                    "-t", str(end - start),
                    trimmed_path
                )
                self.clips[clip_id] = trimmed_path
                print(f"Clip {clip_id} trimmed: {str(start)} - {str(end)}")
                print(f"All clips: {self.clips}")
            except Exception as e:
                raise RuntimeError(f"Error trimming clip {clip_id}: {e}")
        else:
            raise NotImplementedError("Trimming is only implemented for Windows using FFmpeg.")
        
    def render(self, output: str):
        """
        Renders a video from the list of clips.
        It concatenates all clips and saves the output to the specified file.
        :param output: Path to the output video file.
        """
        if not self.clips:
            raise ValueError("No clips to render.")

        try:
            command = [
                helpers.get_path(None, helpers.get_config("PATH_FFMPEG_WINDOWS")),
            ]

            for clip in self.clips:
                command.extend(["-i", clip])
            
            helpers.try_command(
                *command,
                "-filter_complex", f"concat=n={len(self.clips)}:v=1:a=1[outv][outa]",
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                output
            )
        except Exception as e:
            raise RuntimeError(f"Error rendering video: {e}")