# smfteatspuller
Hacky script to pull the TS3 UniqueID details from SMF + TEA to additional TS3 servers.

In my case I'm using this to pull my users' uniqueID directly from the SMF database, inject the IDs to the TS3 sqllite file, then add these clients to the appropriate group.

## usage
Run the script as the ts3 user so it can open the sqlite file in read-write mode.

`# su -u ts3 -c /path/to/sync_SMF_TS.py`
