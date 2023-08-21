import errno
from datetime import datetime
from os import listdir, makedirs, path, unlink, walk
from zipfile import ZIP_DEFLATED, ZipFile

import plug
from requests import Response
from semantic_version import Version

from bgstally.constants import FOLDER_BACKUPS, FOLDER_UPDATES, RequestMethod
from bgstally.debug import Debug
from bgstally.requestmanager import BGSTallyRequest

BACKUPS_KEEP = 3
DATETIME_FORMAT = "%Y-%m-%d-%H-%M-%S"
FILE_LATEST = "latest.zip"
FILE_DISABLE = "disable-auto-update.txt"
URL_PLUGIN_VERSION = "https://api.github.com/repos/aussig/BGS-Tally/releases/latest" # Doesn't include pre-releases or draft releases


class UpdateManager:
    """
    Responsible for handling automatic self-updates of the plugin
    """

    def __init__(self, bgstally):
        self.bgstally = bgstally

        self.updates_folder:str = path.join(self.bgstally.plugin_dir, FOLDER_UPDATES)
        self.backups_folder:str = path.join(self.bgstally.plugin_dir, FOLDER_BACKUPS)
        self.latest_download_file:str = path.join(self.updates_folder, FILE_LATEST)
        self.remote_version:Version = Version.coerce("0")
        self.release_url:str = None
        self.update_available:bool = False

        # Handbrake for local development. Developers - you could lose any unstaged changes if you remove the handbrake. BE WARNED!
        # If you do accidentally overwrite your local folder, the plugin should have made a backup in "backups/"
        if path.exists(path.join(self.bgstally.plugin_dir, FILE_DISABLE)):
            Debug.logger.info(f"Disabling auto-update because {FILE_DISABLE} exists")
            plug.show_error(f"BGS-Tally: Disabling auto-update because {FILE_DISABLE} exists")
            return

        try:
            if not path.exists(self.updates_folder): makedirs(self.updates_folder)
        except OSError as e:
            if e.errno != errno.EEXIST: return
        try:
            if not path.exists(self.backups_folder): makedirs(self.backups_folder)
        except OSError as e:
            if e.errno != errno.EEXIST: return

        self.bgstally.request_manager.queue_request(URL_PLUGIN_VERSION, RequestMethod.GET, callback=self._version_info_received)


    def _version_info_received(self, success:bool, response:Response, request:BGSTallyRequest):
        """
        Latest version info received from the server. Called from a Thread.
        """
        if not success:
            Debug.logger.warning(f"Unable to fetch latest plugin version")
            plug.show_error(f"BGS-Tally: Unable to fetch latest plugin version")
            return

        version_data:dict = response.json()

        if version_data['draft'] == True or version_data['prerelease'] == True:
            # This should never happen because the latest version URL excludes these, but in case GitHub has a wobble
            Debug.logger.info(f"Latest server version is draft or pre-release, ignoring")
            plug.show_error(f"BGS-Tally: Unable to fetch latest plugin version")
            return

        # Check remote assets data structure
        assets:list|None = version_data.get('assets', None)
        if not assets or len(assets) == 0: return

        # Check we have a URL to download the release
        self.release_url = assets[0].get('browser_download_url', None)
        if self.release_url is None: return

        self.remote_version = Version.coerce(version_data['tag_name'])

        Debug.logger.info(f"Retrieved version info, latest={str(self.remote_version)}, current={str(self.bgstally.version)}")

        if self.remote_version > self.bgstally.version:
            # Download the new release
            self.bgstally.request_manager.queue_request(self.release_url, RequestMethod.GET, callback=self._download_received, stream=True)


    def _download_received(self, success:bool, response:Response, request:BGSTallyRequest):
        """
        The download request has initially returned. This is a streamed download so the actual receipt of the file must be chunked
        """
        if not success:
            Debug.logger.warning(f"Unable to fetch latest plugin download")
            plug.show_error(f"BGS-Tally: Unable to fetch latest plugin download")
            return

        try:
            with open(self.latest_download_file, 'wb') as file:
                for chunk in response.iter_content(chunk_size=32768):
                    file.write(chunk)
        except Exception as e:
            Debug.logger.warning(f"Problem saving new version", exc_info=e)
            plug.show_error(f"BGS-Tally: There was a problem saving the new version")
            return

        # Full success, download complete and available
        self.update_available = True

        # Update UI, deferred because we're in a thread
        if self.bgstally.ui.frame: self.bgstally.ui.frame.after(1000, self.bgstally.ui.update_plugin_frame())

        # Perform update
        self._update_plugin()


    def _update_plugin(self):
        """
        Backup the old plugin and extract the new, ready for next launch
        """
        Debug.logger.info(f"Auto updating BGS-Tally from version {self.bgstally.version} to {self.remote_version}")

        self._create_backup()
        self._delete_old_backups()
        self._extract_latest()


    def _create_backup(self):
        """
        Create a backup of the current plugin folder structure
        """
        backup_filepath:str = path.join(self.backups_folder, datetime.now().strftime(DATETIME_FORMAT) + ".zip")
        zip_file:ZipFile = ZipFile(backup_filepath, 'w', ZIP_DEFLATED)

        folder_exclusions:tuple = (FOLDER_UPDATES, FOLDER_BACKUPS)
        folder_prefix_exclusions:tuple = ("__", ".")
        file_prefix_exclusions:tuple = (".")
        file_extension_exclusions:tuple = (".pyc", ".pyo")

        for root, dirs, files in walk(self.bgstally.plugin_dir):
            dirs[:] = [d for d in dirs if d not in folder_exclusions and not d.startswith(folder_prefix_exclusions)]
            for file in files:
                if file.startswith(file_prefix_exclusions) or file.endswith(file_extension_exclusions): continue
                file_path:str = path.join(root, file)
                zip_file.write(file_path, path.relpath(file_path, self.bgstally.plugin_dir))

        zip_file.close()


    def _delete_old_backups(self):
        """
        Delete any backups we no longer need
        """
        backups:list = [f for f in listdir(self.backups_folder) if path.isfile(path.join(self.backups_folder, f))]
        backups = [path.join(self.backups_folder, f) for f in backups] # Add path to each file
        backups.sort(key=lambda x: path.getctime(x)) # Sort by date, oldest first
        backups = backups[:-BACKUPS_KEEP] # Chop the ones we want to keep off the end

        for backup in backups:
            Debug.logger.info(f"Removing backup {backup}")
            unlink(backup)


    def _extract_latest(self):
        """
        Extract the downloaded update over the top of the existing plugin folder
        """
        with ZipFile(self.latest_download_file, "r") as latest:
            latest.extractall(self.bgstally.plugin_dir)
