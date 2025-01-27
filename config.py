# safe_repo
# Note if you are trying to deploy on vps then directly fill values in ("")

from os import getenv

API_ID = int(getenv("API_ID", "23151406"))
API_HASH = getenv("API_HASH", "0893a87614fae057c8efe7b85114f45a")
BOT_TOKEN = getenv("BOT_TOKEN", "8109110306:AAH8iB0jx8b2KESo41J-Zgx6NcT7zJqWGf0")
OWNER_ID = list(map(int, getenv("OWNER_ID", "8118877872").split()))
MONGO_DB = getenv("MONGO_DB", "mongodb://ahmedalsaltani30:ahmedabcd074@cluster0-shard-00-00.quu8v.mongodb.net:27017,cluster0-shard-00-01.quu8v.mongodb.net:27017,cluster0-shard-00-02.quu8v.mongodb.net:27017/?ssl=true&replicaSet=atlas-s98j2a-shard-0&authSource=admin&retryWrites=true&w=majority&appName=Cluster0")
LOG_GROUP = getenv("LOG_GROUP", "-1002264676623")
CHANNEL_ID = int(getenv("CHANNEL_ID", "-1002264676623"))
