#
# token-based-authentication.py
#
# The code sample below explains the process of Creation, Download , Revoke and Usage of API Tokens.
# When an API Token is expired, a new API Token will have to be created as we do not allow refreshing the existing tokens in Phase 1.

import os
import requests
import json
import re
import sys, getopt
from client import VcoRequestManager
from client import ApiException

# EDIT THESE
VCO_HOSTNAME = 'vcoX.velocloud.net'
OPERATOR_USER_ID = 1
ENTERPRISE_USER_ID = 1
ENTERPRISE_PROXY_ID = 1
ENTERPRISE_ID = 1
NAME = 'API_TOKEN_NAME'
LIFETIMEMS = 300000



class ApiTokenAuth(VcoRequestManager):
    def __init__(self, hostname, params, userType):
        super(ApiTokenAuth, self).__init__(hostname)

        self._TOKEN_ID = ""
        self._headers = { "Content-Type": "application/json" }
        self._params = params
        self._userType = userType
        self._res = {}

    def call_api(self, method, params):
        """
        Build and submit a request
        Returns method result as a Python dictionary
        """
        self._seqno += 1
        method = self._clean_method_name(method)
        payload = { "jsonrpc": "2.0",
                    "id": self._seqno,
                    "method": method,
                    "params": params }

        if method in ("liveMode/readLiveData", "liveMode/requestLiveActions", "liveMode/clientExitLiveMode"):
            url = self._livepull_url
        else:
            url = self._portal_url

        r = self._session.post(url, headers=self._headers,
                               data=json.dumps(payload), verify=self._verify_ssl)

        print(r)

        response_dict = r.json()
        if "error" in response_dict:
            raise ApiException(response_dict["error"]["message"])
        return response_dict["result"]

    def execute_token_actions(self):

        prefix = ""
        if self._userType == "OPERATOR" :
            prefix = "network"
        elif self._userType == "ENTERPRISE" :
            prefix = "enterprise"
        elif self._userType == "PARTNER" or self._userType == "MSP":
            prefix = "enterpriseProxy"

        # 1. Create API Token
        try:
            self._res = self.call_api(prefix + '/createApiToken', self._params)
        except ApiException as e:
            print(e)
            return

        # 2. Download API Token
        try:
            self._params.update({"id": self._res['id']})
            self._res = self.call_api(prefix + '/downloadApiToken', self._params)
        except ApiException as e:
            print(e)
            return

        # Contruct the Authorization header
        if 'token' in self._res:
            self._headers.update( { 'Authorization':"Token " + self._res['token'] })

        #Clear session cookies, using Token based authentication
        self._session.cookies.clear()

        # The response of the APIs below will indicate If the token is expired or invalid.
        # 4. Get API Tokens
        try:
            self._res = self.call_api(prefix  + '/getApiTokens', {})
        except ApiException as e:
            print(e)
            return

        # 5. Revoke API Token
        try:
            self._res = self.call_api(prefix  + '/revokeApiToken', self._params)
        except ApiException as e:
            print(e)
            return


def main(argv):
    username = ""
    password = ""
    userType = ""
    isOperator = False
    params = {}
    try:
        opts,args = getopt.getopt(argv, 'o:v',["username=","password=", "userType="] )
    except getopt.GetoptError:
        print('token-based-authentication.py --username= <username> --password=<password> --userType= <userType>]')
        sys.exit(2)

    for opt,arg in opts:
        if opt == '--username':
            username = arg
        if opt == '--password':
            password = arg
        if opt == '--userType':
            userType = arg

    #API Token Operations
    if userType == "OPERATOR":
        params = {"operatorUserId": OPERATOR_USER_ID, "name": NAME, "lifetimeMs": LIFETIMEMS}
        isOperator = True
    elif userType == "ENTERPRISE":
        params = {"enterpriseUserId": ENTERPRISE_USER_ID, "enterpriseId": ENTERPRISE_ID, "name": NAME, "lifetimeMs": LIFETIMEMS}
    elif userType == "PROXY" or userType == "MSP":
        params = {"enterpriseUserId": ENTERPRISE_USER_ID, "enterpriseProxyId": ENTERPRISE_PROXY_ID, "name": NAME, "lifetimeMs": LIFETIMEMS}


    #Executing API Token Actions
    apiClient = ApiTokenAuth(VCO_HOSTNAME, params, userType)
    apiClient.authenticate(username, password, isOperator)
    apiClient.execute_token_actions()


if __name__ == "__main__":
    main(sys.argv[1:])


