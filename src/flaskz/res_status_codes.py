# response status for client use
# if value is tuple, the second value will be returned as the error message

# database
db_add_err = 'db_add_err', 'Database Add Error'
db_delete_err = 'db_delete_err', 'Database Delete Error'
db_update_err = 'db_update_err', 'Database Update Error'
db_query_err = 'db_query_err', 'Database Query Error'

db_data_not_found = 'db_data_not_found', 'Data Not Found'
db_data_already_exist = 'db_data_already_exist', 'Data Already Exists'
db_data_in_use = 'db_data_in_use', 'Data In Use'

# remote request
api_request_err = "api_req_err", 'Remote api request error'

# error
uri_unauthorized = 'uri_unauthorized', 'Unauthorized'  # 401 Unauthorized, need login
uri_forbidden = 'uri_forbidden', 'Forbidden'  # 403 Forbidden, need permission
uri_not_found = 'uri_not_found', 'Not Found'  # 404 Not Found
method_not_allowed = 'method_not_allowed', 'Method Not Allowed'  # 405 HTTP method is not supported
internal_server_error = 'internal_server_error', 'Internal Server Error'  # 500
bad_request = 'bad_request', 'Bad Request'  # 400 Bad Request, payload error

# account
account_not_found = 'account_not_found', 'No Account Found'
account_disabled = 'account_disabled', "Account Disabled"
account_verify_err = 'account_verify_err', 'Wrong Password'

# others
