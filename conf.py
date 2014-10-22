'''
print -- CSLabs Print Server
conf -- Configuration

This module contains some variables that can be modified to configure the web application.
In general, these variables are used to provide defaults for actions that are done
via the web interface. They should not be used in any other scenario, particularly in
places where the web interface is irrelevant.

The following are defined:
-DEFAULT_BALANCE is the balance given to newly created accounts.
'''

DEFAULT_BALANCE = 200
