import sqlite3
import time

from flask import Flask
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ..log import flaskz_logger
from ..utils import Attribute

DBSession = sessionmaker(autocommit=False)

ModelBase = declarative_base()


def init_model(app):
    """
    Initialize the database
    """
    is_app = isinstance(app, Flask)
    if is_app:
        app_config = app.config
    else:
        app_config = app
    # app_config = app.config
    database_uri = app_config.get('FLASKZ_DATABASE_URI')

    # enable sqlite foreign key
    # if database_uri.startswith('sqlite'):
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        if isinstance(cursor, sqlite3.Cursor):  # for multiple db connect
            cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    try:
        engine = create_engine(database_uri, echo=app_config.get('FLASKZ_DATABASE_ECHO'), pool_recycle=app_config.get('FLASKZ_DATABASE_POOL_RECYCLE'))
        # Session.configure(bind=engine)
        DBSession.configure(binds={ModelBase: engine})  # for multiple db
        with engine.connect():  # connect test
            flaskz_logger.info('Database ' + database_uri + ' is ready\n')
    except Exception as e:
        flaskz_logger.exception('Connect to database ' + database_uri + ' error\n')
        return

    if not is_app:
        return

    @app.teardown_appcontext
    def teardown_db(exception):
        """
        When the request ends, close the db session.
        :param exception:
        :return:
        """
        close_db_session()

    if app_config.get('FLASKZ_DATABASE_DEBUG') is True:
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('_query_start_time', []).append(time.perf_counter())

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            end_time = time.perf_counter()
            start_time = conn.info['_query_start_time'].pop(-1)
            append_debug_queries(Attribute(**{
                'start_time': start_time,
                'end_time': end_time,
                'duration': (end_time - start_time) * 1000,  # ms
                'statement': statement,
                'parameters': parameters,
                'context': context,
            }))

        # if duration > db_slow_time:
        #     app_logger.warning('Slow query: %s\nParameters: %s\nDuration: %fms\n' % (statement, parameters, duration))

        db_slow_time = app_config.get('FLASKZ_DATABASE_DEBUG_SLOW_TIME', -1)  # set config['FLASKZ_DATABASE_DEBUG_SLOW_TIME'] to enable
        db_access_times = app_config.get('FLASKZ_DATABASE_DEBUG_ACCESS_TIMES', -1)  # set config['FLASKZ_DATABASE_DEBUG_ACCESS_TIMES'] to enable
        if db_slow_time > 0 or db_access_times > 0:
            @app.after_request
            def after_request(response):
                queries = get_debug_queries()
                times = len(queries)
                if times > 0:
                    if 0 < db_access_times < times:
                        flaskz_logger.warning('Query Times:\n' + str(times))

                    if db_slow_time > 0:
                        slow_queries = []
                        for query in queries:
                            if query.duration > db_slow_time:
                                slow_queries.append('--Duration: %fms\n--Statement:%s\n--Parameters: %s' % (query.duration, query.statement, query.parameters))
                        if len(slow_queries) > 0:
                            flaskz_logger.warning('Slow queries:\n' + ('\n'.join(slow_queries)))
                return response


from ._base import *
from ._model import *
from ._util import *
