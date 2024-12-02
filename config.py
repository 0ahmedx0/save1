# safe_repo
# Note if you are trying to deploy on vps then directly fill values in ("")

from os import getenv

API_ID = int(getenv("API_ID", "21417190"))
API_HASH = getenv("API_HASH", "49cd487bc068aa8ec3cd060a587017b0")
BOT_TOKEN = getenv("BOT_TOKEN", "7518380330:AAH2Xub5gKYf4jYGT0-cJxdqotPpBL1rLLA")
OWNER_ID = list(map(int, getenv("OWNER_ID", "8077445518").split()))
MONGO_DB = getenv("MONGO_DB", "mongodb://ahmedalsaltani30:ahmedabcd074@cluster0-shard-00-00.quu8v.mongodb.net:27017,cluster0-shard-00-01.quu8v.mongodb.net:27017,cluster0-shard-00-02.quu8v.mongodb.net:27017/?ssl=true&replicaSet=atlas-s98j2a-shard-0&authSource=admin&retryWrites=true&w=majority&appName=Cluster0")
LOG_GROUP = getenv("LOG_GROUP", "-1002316651575")
CHANNEL_ID = int(getenv("CHANNEL_ID", "-1002316651575"))
