# pylint: disable=too-few-public-methods

"""PynamoDB models for testing."""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    UTCDateTimeAttribute,
    DynamicMapAttribute,
    ListAttribute,
)


class ChartMetadata(DynamicMapAttribute):
    """Chart metadata"""

    x_axis_title = UnicodeAttribute()
    y_axis_title = UnicodeAttribute()
    x_axis_column_name = UnicodeAttribute()
    y_axis_column_names = ListAttribute(of=UnicodeAttribute)


class User(Model):
    """User model"""

    class Meta:
        """Meta class"""

        table_name = "user"
        region = "us-east-1"

    username = UnicodeAttribute(hash_key=True)
    email = UnicodeAttribute()
    password = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    charts = ChartMetadata()
    names = ListAttribute(of=UnicodeAttribute)


class Post(Model):
    """Post model"""

    class Meta:
        """Meta class"""

        table_name = "post"
        region = "us-east-1"

    id = NumberAttribute(hash_key=True)
    title = UnicodeAttribute()
    body = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    username = UnicodeAttribute(range_key=True)
