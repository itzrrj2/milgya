import motor.motor_asyncio
from config import DB_URI, DB_NAME
import time

# MongoDB setup
dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]
user_data = database['users']

# Default verify status
default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

# Default user data
def new_user(id):
    return {
        '_id': id,
        'verify_status': default_verify.copy(),  # Use a copy to avoid modifying default_verify
        'download_count': 0,  # Track number of free downloads used
        'shortlink_verified': False,  # Track if user has bypassed shortlink
        'shortlink_expiry': 0,  # When the shortlink verification expires
        'premium': False,  # Premium status
        'premium_expiry': 0,  # When premium membership expires
        'channel_membership': {
            'Ashlynn_Repository': False,
            'Ashlynn_RepositoryBot': False
        }
    }

# Check if a user is present in the database
async def present_user(user_id: int):
    found = await user_data.find_one({'_id': user_id})
    return bool(found)

# Add a new user to the database
async def add_user(user_id: int):
    user = new_user(user_id)
    await user_data.insert_one(user)

# Get user data
async def get_user(user_id: int):
    user = await user_data.find_one({'_id': user_id})
    if not user:
        await add_user(user_id)
        return new_user(user_id)
    return user

# Update user data
async def update_user(user_id: int, data):
    await user_data.update_one({'_id': user_id}, {'$set': data})

# Get download count
async def get_download_count(user_id: int):
    user = await get_user(user_id)
    return user.get('download_count', 0)

# Increment download count
async def increment_download_count(user_id: int):
    await user_data.update_one({'_id': user_id}, {'$inc': {'download_count': 1}})

# Check if user is premium
async def is_premium(user_id: int):
    user = await get_user(user_id)
    if user.get('premium', False) and user.get('premium_expiry', 0) > time.time():
        return True
    
    # If premium has expired, update the status
    if user.get('premium', False) and user.get('premium_expiry', 0) <= time.time():
        await update_user(user_id, {'premium': False})
        return False
    
    return False

# Add premium to user
async def add_premium(user_id: int, months: int):
    user = await get_user(user_id)
    current_expiry = user.get('premium_expiry', 0)
    
    # If premium is already active, extend it
    if current_expiry > time.time():
        new_expiry = current_expiry + (months * 30 * 24 * 60 * 60)  # Convert months to seconds
    else:
        new_expiry = time.time() + (months * 30 * 24 * 60 * 60)
    
    await update_user(user_id, {'premium': True, 'premium_expiry': new_expiry})
    return new_expiry

# Remove premium from user
async def remove_premium(user_id: int):
    await update_user(user_id, {'premium': False, 'premium_expiry': 0})

# Check if shortlink is verified
async def is_shortlink_verified(user_id: int):
    user = await get_user(user_id)
    if user.get('shortlink_verified', False) and user.get('shortlink_expiry', 0) > time.time():
        return True
    
    # If shortlink verification has expired, update the status
    if user.get('shortlink_verified', False) and user.get('shortlink_expiry', 0) <= time.time():
        await update_user(user_id, {'shortlink_verified': False})
        return False
    
    return False

# Set shortlink verification
async def set_shortlink_verified(user_id: int, hours: int = 12):
    expiry = time.time() + (hours * 60 * 60)  # Convert hours to seconds
    await update_user(user_id, {'shortlink_verified': True, 'shortlink_expiry': expiry})

# Update channel membership
async def update_channel_membership(user_id: int, channel: str, status: bool):
    user = await get_user(user_id)
    membership = user.get('channel_membership', {})
    membership[channel] = status
    await update_user(user_id, {'channel_membership': membership})

# Check channel membership
async def check_channel_membership(user_id: int, channel: str):
    user = await get_user(user_id)
    membership = user.get('channel_membership', {})
    return membership.get(channel, False)

# Check all required channel memberships
async def check_all_channel_memberships(user_id: int):
    user = await get_user(user_id)
    membership = user.get('channel_membership', {})
    return all(membership.values())

# Retrieve verify status for a user
async def db_verify_status(user_id):
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('verify_status', default_verify)
    return default_verify

# Update verify status for a user
async def db_update_verify_status(user_id, verify):
    await user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

# Retrieve a list of all user IDs in the database
async def full_userbase():
    user_docs = user_data.find()
    user_ids = [doc['_id'] async for doc in user_docs]
    return user_ids

# Delete a user from the database
async def del_user(user_id: int):
    await user_data.delete_one({'_id': user_id})
