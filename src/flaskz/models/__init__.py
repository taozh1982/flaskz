import sqlite3
import time
from datetime import datetime

from flask import Flask
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine import ExceptionContext
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
        engine_kwargs = {}
        custom_engine_kwargs = app_config.get('FLASKZ_DATABASE_ENGINE_KWARGS')  # @2023-02-27: add FLASKZ_DATABASE_ENGINE_KWARGS config
        if type(custom_engine_kwargs) is dict:
            engine_kwargs.update(custom_engine_kwargs)

        for engine_key, config_key in {'echo': 'FLASKZ_DATABASE_ECHO',
                                       'pool_recycle': 'FLASKZ_DATABASE_POOL_RECYCLE',
                                       'pool_pre_ping': 'FLASKZ_DATABASE_POOL_PRE_PING'}.items():  # @2023-02-01: add pool_pre_ping config
            if config_key in app_config:
                engine_kwargs[engine_key] = app_config.get(config_key)

        engine = create_engine(database_uri, **engine_kwargs)
        DBSession.configure(binds={ModelBase: engine})  # for multiple db

        with engine.connect():  # connect test
            flaskz_logger.info('Database ' + database_uri + ' is ready\n')

        # handle disconnect error
        engine_err_info = {}

        @event.listens_for(engine, "handle_error")
        def handle_engine_error(context: ExceptionContext):  # @2023-02-01: add error handler
            flaskz_logger.error('Engine error:\n' + str(context.original_exception))
            if engine_kwargs.get('pool_pre_ping') is not True:
                if not context.connection or context.sqlalchemy_exception.connection_invalidated:
                    now = datetime.now().timestamp()
                    last_connect_time = engine_err_info.get('connect_time')
                    if last_connect_time is None or now - last_connect_time > 1:  # interval >1s
                        engine_err_info['connect_time'] = now
                        engine.connect()  # reconnect

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
