import helpers

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
                helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FFPROBE_WINDOWS")),
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                self.clips[clip_id],
                return_output=True
            )
            return float(output)
        except Exception as e:
            raise RuntimeError(f"Error getting length of clip {clip_id}: {e}")
    
    def reset_clips(self):
        """
        Reset the list of video clips.
        """
        self.clips = []

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
        
    def trim(self, clip_id: int, start: float, end: float):
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
                # Get the clip's file extension
                ext = self.clips[clip_id].split(".")[-1]
                trimmed_path = self.clips[clip_id].replace(f".{ext}", f"_trimmed_{start}_{end}.{ext}")
                helpers.try_command(
                    helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FFMPEG_WINDOWS")),
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

    def export_to_file(self):
        """
        Exports the video clips to a text file for ffmpeg concat (copy mode only).
        """
        output_file = helpers.get_path(
            None,
            helpers.get_config("DEFAULT_OUTPUT_FILENAME"),
            "clips.txt"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            for clip in self.clips:
                normalized_clip = clip.replace("\\", "/")
                while "//" in normalized_clip:
                    normalized_clip = normalized_clip.replace("//", "/")
                f.write(f"file '{normalized_clip}'\n")
        return output_file


    def render(self, output: str, reencode: bool = True, target_width: int = 1280, target_height: int = 720, fps: int = 30):
        """
        Concatenate all clips and save to 'output'.
        - reencode=False  -> fast concat (requires identical input formats)
        - reencode=True   -> safe concat via filter_complex (handles mixed codecs/sizes)
        """
        if not self.clips:
            raise ValueError("No clips to render.")

        try:
            ffmpeg = helpers.get_path(helpers.get_app_folder(), helpers.get_config("PATH_FFMPEG_WINDOWS"))

            if not reencode:
                # ---------- FAST PATH: concat demuxer + stream copy ----------
                file_list = self.export_to_file()
                command = [
                    ffmpeg,
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", file_list,
                    "-c", "copy",
                    output,
                ]
                helpers.try_command(*command, return_output=True)
                return

            # ---------- SAFE PATH: concat filter + re-encode ----------
            # Build inputs
            command = [ffmpeg, "-y"]
            for clip in self.clips:
                command.extend(["-i", clip])

            n = len(self.clips)
            w, h = int(target_width), int(target_height)

            # Build per-input normalization chains:
            # - scale to fit, pad to exact size
            # - reset PTS (fixes "very long" or "black" segments)
            # - resample audio to a stable layout/rate
            v_chains = []
            a_chains = []
            for i in range(n):
                v_chains.append(
                    f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
                    f"setsar=1,setpts=PTS-STARTPTS[v{i}]"
                )
                # If some inputs lack audio, this will error. If you have silent clips,
                # give them a silent track first (ask if you need that handled automatically).
                a_chains.append(
                    f"[{i}:a]aresample=async=1:min_comp=0.001:first_pts=0,asetpts=PTS-STARTPTS[a{i}]"
                )

            # Concat assembly
            pairs = "".join(f"[v{i}][a{i}]" for i in range(n))
            filter_complex = ";".join(v_chains + a_chains) + ";" + \
                            f"{pairs}concat=n={n}:v=1:a=1[outv][outa]"

            command.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                "-r", str(fps),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-ac", "2",
                "-movflags", "+faststart",
                output,
            ])

            helpers.try_command(*command, return_output=True)

        except Exception as e:
            raise RuntimeError(f"Error rendering video: {e}")
