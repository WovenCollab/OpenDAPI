"""SQLAlchemy Core fixtures."""

from sqlalchemy import MetaData
from sqlalchemy import Table, Column, Integer, String, ForeignKey

metadata_obj = MetaData(schema="my_schema")
user_account = Table(
    "user_account",
    metadata_obj,
    Column("account_id", Integer, primary_key=True),
    Column("account_name", String(16), nullable=False),
    Column("email_address", String(60)),
    Column("nickname", String(50), nullable=False),
)

user_posts = Table(
    "user_posts",
    metadata_obj,
    Column("post_id", Integer, primary_key=True),
    Column("user_account_id", Integer, ForeignKey("user_account.account_id")),
    Column("post_title", String(200), nullable=False),
)
