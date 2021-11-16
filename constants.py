from config import PROJECT_NAME


SENTRY_ENV_NAME = f"{PROJECT_NAME}_invite_role_bot".lower()
INV_TO_ROLES = "INVITES_TO_ROLES"
ROLE_ID_SEPARATOR = "|"  # this separator will be used internally to split multiple roles from string
GUILD_INDEX = 0
