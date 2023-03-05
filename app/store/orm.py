from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

_convention = {
    'all_column_names': lambda constraint, table: '.'.join([
        column.name for column in constraint.columns.values()
    ]),
    'ix': 'ix-%(table_name)s-%(all_column_names)s',
    'uq': 'uq-%(table_name)s-%(all_column_names)s',
    'ck': 'ck-%(table_name)s-%(constraint_name)s',
    'fk': 'fk-%(table_name)s-%(all_column_names)s-%(referred_table_name)s',
    'pk': 'pk-%(table_name)s'
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_convention)
