# Google-Drive-Mirror - Mirror/Indexer of Gdrive with FastAPI
# Copyright (C) 2025 kaif-00z
#
# This file is a part of < https://github.com/kaif-00z/Google-Drive-Mirror/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/kaif-00z/Google-Drive-Mirror/blob/main/LICENSE>.


from decouple import config


class Var:
    IS_SERVICE_ACCOUNT = config("IS_SERVICE_ACCOUNT", default=False, cast=bool)
    ROOT_FOLDER_ID = config("ROOT_FOLDER_ID")
