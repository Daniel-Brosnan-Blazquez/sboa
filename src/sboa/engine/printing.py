"""Runtime helpers for SBOA, part of the BOA suite.

Written by Daniel Brosnan Blázquez.
"""

from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.sql.sqltypes import String, DateTime, NullType
from sqlalchemy.dialects import postgresql


class StringLiteral(String):
    """
    Class to teach SQLAlchemy how to literalize various things.
    """
    def literal_processor(self, dialect):

        super_processor = super(StringLiteral, self).literal_processor(dialect)

        # Always return the casting to string
        return str

class LiteralDialect(DefaultDialect):
    """
    Class to implement the dialect needed for every column type
    """
    colspecs = {
        # prevent various encoding explosions
        String: StringLiteral,
        # teach SA about how to literalize a datetime
        DateTime: StringLiteral,
        # don't format py2 long integers to NULL
        NullType: StringLiteral,
        postgresql.UUID: StringLiteral
    }

def literal_query(statement):
    """
    Method to print raw SQL statements from the SQLAlchemy statements
    :param statement: SQLAlchemy statement
    :type statement: sqlalchemy.sql.annotation

    Method used for debugging purpuses (not open to external usage)
    """
    sql_statement = statement.compile(dialect=LiteralDialect(), compile_kwargs={'literal_binds': True}).string
    return sql_statement
