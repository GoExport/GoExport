import argparse
from math import gcd
from pathlib import Path


def parse_resolution(value: str) -> tuple[int, int]:
	try:
		width, height = map(int, value.lower().split("x"))

		if width <= 0 or height <= 0:
			raise ValueError

		return width, height

	except ValueError as exc:
		raise argparse.ArgumentTypeError(
			f"Resolution must be in the format WIDTHxHEIGHT "
			f"(e.g., 1920x1080), got '{value}'."
		) from exc


def existing_file(path: str) -> Path:
	file_path = Path(path)

	if not file_path.is_file():
		raise argparse.ArgumentTypeError(
			f"'{path}' does not exist or is not a file."
		)

	return file_path


def existing_directory(path: str) -> Path:
	dir_path = Path(path)

	if not dir_path.is_dir():
		raise argparse.ArgumentTypeError(
			f"'{path}' does not exist or is not a directory."
		)

	return dir_path


def calculate_aspect_ratio(width: int, height: int) -> tuple[int, int]:
	common_divisor = gcd(width, height)

	return (
		width // common_divisor,
		height // common_divisor,
	)


def resolve_output_path(output: Path, video_format: str) -> Path:
	if output.suffix.lower() != f".{video_format}":
		final_output_path = Path(f"{output}.{video_format}")
	else:
		final_output_path = output

	final_output_path.parent.mkdir(parents=True, exist_ok=True)

	return final_output_path
