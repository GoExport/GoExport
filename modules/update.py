import requests
import helpers
from modules.logger import logger

class Update:
    def __init__(self):
        repo = helpers.get_config("APP_REPO")
        self.repo_api = f"https://api.github.com/repos/{repo}/releases/latest"
        self.version_key = "latest_version"

    def _check_for_update(self):
        try:
            response = requests.get(self.repo_api, timeout=10)
            response.raise_for_status()
            data = response.json()

            latest_version = data.get("tag_name", "").lstrip("v")
            local_version = helpers.get_config("APP_VERSION").lstrip("v")

            if local_version != latest_version:
                helpers.save("update_needed", latest_version)
                return latest_version
            else:
                return False
        except Exception as e:
            logger.error(f"Error when checking for updates: {e}")

    def _should_check_for_updates(self):
        current_time = helpers.get_timestamp("Update check")
        adjusted = current_time + 3_600_000  # +1 hour
        last_checked = helpers.load("updates_checked", 0)

        if current_time < last_checked:
            self.current_update = helpers.load("update_needed", 0)
            return False

        helpers.save("updates_checked", adjusted)
        return True

    def check(self):
        if self._should_check_for_updates():
            return self._check_for_update()
        else:
            return self.current_update
