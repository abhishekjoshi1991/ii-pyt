import os
from dotenv import load_dotenv
load_dotenv()
remote_host = os.getenv("HOST")
remote_user= os.getenv("DB_USER")
remote_password = os.getenv("DB_PASSWORD")
remote_database= os.getenv("DATABASE")

local_host = os.getenv("HOST_LOCAL")
local_user= os.getenv("DB_USER_LOCAL")
local_password = os.getenv("DB_PASSWORD_LOCAL")
local_database= os.getenv("DATABASE_LOCAL")
SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{local_user}:{local_password}@{local_host}/{local_database}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

SQLALCHEMY_DATABASE_URI_2 = f"mysql+pymysql://{remote_user}:{remote_password}@{remote_host}/{remote_database}"
email_delimiter_1 = '@' 
email_delimiter_2 = '-' # set this value to None if user do not want to split email at '-'

