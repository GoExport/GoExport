from pathlib import Path


class AssetResolver:
    def __init__(
        self,
        asset_path: str | Path,
        store_path: str | Path,
    ):
        self.asset_path = Path(asset_path)
        self.store_path = Path(store_path)
        
    def _resolve_theme(self, filename: str) -> Path:
        theme, asset = filename.split(".", 1)

        path = (
            self.store_path /
            theme /
            "sound" /
            asset
        )

        if not path.is_file():
            raise FileNotFoundError(
                f"Theme asset not found: {filename}"
            )

        return path

    def _resolve_ugc(self, filename: str) -> Path:
        asset = filename.removeprefix("ugc.")

        path = self.asset_path / asset

        if not path.is_file():
            raise FileNotFoundError(
                f"UGC asset not found: {filename}"
            )

        return path

    def resolve(self, asset_id: str) -> Path:
        if asset_id.startswith("ugc."):
            return self._resolve_ugc(asset_id)

        return self._resolve_theme(asset_id)