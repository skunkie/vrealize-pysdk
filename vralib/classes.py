# TODO implement logging

__author__ = 'Russell Pope'


import json
import requests

from vralib.vraexceptions import InvalidToken

try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
except ImportError:
    pass


class Session(object):
    """
    Used to store vRA login session to a specific tenant. The class should be invoked via cls.login()

    This class also includes a series of methods that are helpful in managing the vRA environment.

    The included methods are:

    Session._request(url, request_method="POST", payload)
        Typically used by the class itself to post requests to the vRA REST API

    Session._request(url)
        Used by the class to retrieve data from the vRA REST API

    Session.get_business_groups()
        Returns a dictionary of all business groups available to the logged in user.

    Session.get_entitledcatalogitems()
        Returns a dictionary of all of the catalog items available to the logged in user.

    Session.get_catalogitem_byname(name)
        Returns a dictionary of catalog items containing the string in 'name'

    """

    def __init__(self, username, cloudurl, tenant, auth_header, ssl_verify):
        """Initialization of the Session class.

        The password is intentionally not stored in this class since we only really need the token.

        When creating instances of this class you should invoke the Session.login() @classmethod. 
        If you invoke Session.__init__() directly you'll need to know what your bearer token is ahead of time.  

        :param username: The username is stored here so it can be passed easily into other methods in other classes.
        :param cloudurl: Stores the FQDN of the vRealize Automation server
        :param tenant: Stores the tenant to log into. If left blank it will default to vsphere.local
        :param auth_header: Stores the actual Bearer token to be used in subsequent requests.

        :return:
        """

        self.username = username
        self.cloudurl = cloudurl
        self.tenant = tenant
        self.token = auth_header
        self.headers = {'Content-type': 'Application/json',
                        'Accept': 'Application/json',
                        'Authorization': self.token}
        self.ssl_verify = ssl_verify

    @classmethod
    def login(cls, username, password, cloudurl, tenant=None, ssl_verify=True):
        """
        Takes in a username, password, URL, and tenant to access a vRealize Automation server AP. These attributes
        can be used to send or retrieve data from the vRealize automation API.

        Basic usage:

        vra = vralib.Session.login(username, password, cloudurl, tenant, ssl_verify=False)

        This creates a Session object called 'vra' which can now be used to access all of the methods in this class.

        :param username: A username@domain with sufficient rights to use the API
        :param password: The password of the user
        :param cloudurl: The vRealize automation server. Should be the FQDN.
        :param tenant: the tenant ID to be logged into. If left empty it will default to vsphere.local
        :param ssl_verify: Enable or disable SSL verification.

        :return: Returns a class that includes all of the login session data (token, tenant and SSL verification)
        """

        if not tenant:
            tenant = 'vsphere.local'

        r = None

        try:
            if not ssl_verify:
                try:
                    requests.packages.urllib3.disable_warnings(
                        InsecureRequestWarning)
                except AttributeError:
                    pass
            r = requests.post(
                url='https://%s/identity/api/tokens' % cloudurl,
                headers={'Content-type': 'Application/json',
                         'Accept': 'Application/json'},
                verify=ssl_verify,
                data=json.dumps({
                    "tenant": tenant,
                    "username": username,
                    "password": password
                })
            )

            vratoken = json.loads(r.content)

            if 'id' in vratoken.keys():
                auth_header = 'Bearer %s' % vratoken['id']
                return cls(username, cloudurl, tenant, auth_header, ssl_verify)
            else:
                raise InvalidToken('No bearer token found in response. Response was:',
                                   json.dumps(vratoken))

        except requests.exceptions.ConnectionError:
            raise requests.exceptions.ConnectionError(
                'Unable to connect to server %s.' % cloudurl)

        except requests.exceptions.HTTPError:
            raise requests.exceptions.HTTPError(
                'HTTP error. Status code was:', r.status_code)

    def _request(self, url, request_method='GET', payload=None, **kwargs):
        """
        Generic requestor method for all of the HTTP methods. This gets invoked by pretty much everything in the API.
        You can also use it to do anything not yet implemented in the API. For example:
        (assuming an instance of this class called vra)

        out = vra._request(url='https://vra-01a.corp.local/properties-service/api/propertygroups')
        print(json.dumps(out, indent=4))

        :param url: The complete URL for the requested resource
        :param request_method: An HTTP method that is either PUT, POST or GET
        :param payload: Used to store a resource that is used in either POST or PUT operations
        :param kwargs: Unused currently

        :return: A python dictionary containing the response JSON
        """

        if request_method == "PUT" or "POST" and payload:
            if type(payload) == dict:
                payload = json.dumps(payload)

            r = requests.request(request_method,
                                 url=url,
                                 headers=self.headers,
                                 verify=self.ssl_verify,
                                 data=payload)

            if not r.ok:
                raise requests.exceptions.HTTPError(
                    'HTTP error. Status code was:', r.status_code, r.content)

        elif request_method == "GET":
            r = requests.request(request_method,
                                 url=url,
                                 headers=self.headers,
                                 verify=self.ssl_verify)

            if not r.ok:
                raise requests.exceptions.HTTPError(
                    'HTTP error. Status and content:', r.status_code, r.content)

        elif request_method == "DELETE":
            r = requests.request(request_method,
                                 url=url,
                                 headers=self.headers,
                                 verify=self.ssl_verify)

            if not r.ok:
                raise requests.exceptions.HTTPError(
                    'HTTP error. Status code was:', r.status_code)

        else:
            raise Exception('Method %s is not implemented.' % request_method)

        return json.loads(r.content)

    def _iterate_pages(self, url):
        """
        Iterates over pages of the HTTP Response.

        :return: a list of requested items from the `content` of the response.
        """

        result = []

        n = 1
        while True:
            page = self._request('%s?page=%s' % (url, n))
            result = result + page['content']
            if n <= page['metadata']['totalPages']:
                break
            n += 1

        return result

    def get_business_groups(self):
        """
        Retrieves a list of all vRA business groups for the currently logged in user.

        :return: python dictionary with the JSON response contents.
        """

        url = 'https://%s/identity/api/tenants/%s/subtenants' % (
            self.cloudurl, self.tenant)
        return self._iterate_pages(url)

    def get_businessgroup_byname(self, name):
        """
        Loop through all vRA business groups until you find the one with the specified name.
        This method allows you to "filter" returned business groups via a partial match.
        """

        business_groups = self.get_business_groups()

        result = []

        for i in business_groups:
            target = i['name']
            if name.lower() in target.lower():
                element = {'name': i['name'], 'id': i['id']}
                result.append(element)

        return result

    def get_businessgroup_fromid(self, group_id):
        """Lists a business group using the group id.

        :return: A python dictionary of the selected business group details
        """

        url = 'https://%s/identity/api/tenants/%s/subtenants/%s' % (
            self.cloudurl, self.tenant, group_id)
        return self._request(url)

    def delete_businessgroup_fromid(self, group_id):
        """
        Deletes a business group from vRealize Automation if all other objects have been removed.

        :return:
        """

        url = 'https://%s/identity/api/tenants/%s/subtenants/%s' % (
            self.cloudurl, self.tenant, group_id)
        return self._request(url, request_method='DELETE')

    def get_entitled_catalog_items(self):
        """
        Retrieves a dictionary of all the currently available catalog items for the logged in user/tenant.
        This can result in multi-page output so I've added some basic pagination here.

        :return:
        """

        # TODO update the output dict's page number to reflect a list of page numbers iterated through
        # TODO add exception handling for when you're not actually entitled to anything.
        # TODO probably need to deprecate this function
        url = 'https://%s/catalog-service/api/consumer/entitledCatalogItems' % self.cloudurl
        return self._iterate_pages(url)

    def get_catalogitem_byname(self, name, catalog=False):
        """Loop through catalog items until you find the one with the specified name.        

        This method allows you to "filter" returned catalog items via a partial match.

        Basic usage:

        log into vra:

        vra = vralib.Session.login(username, password, cloudurl, tenant, ssl_verify=False)

        catalog_offerings = vra.get_catalogitem_byname(name='cent')

        This will store any catalog items with 'cent' anywhere in the name.

        Optionally this method can be passed an object that includes the catalog:

        vra = vralib.Session.login(username, password, cloudurl, tenant, ssl_verify=False)

        catalog_offerings = vra.get_catalogitem_byname(name='cent', vra.get_get_entitledcatalogitems())

        :param name: A required string that will be used to filter the return to items that contain the string.
        :param catalog: An optional dictionary of all of the catalog items available to the user.

        :return: Returns a list of dictionaries that contain the catalog item and ID
        """

        if not catalog:
            catalog = self.get_entitled_catalog_items()

        result = []

        for i in catalog:
            target = i['catalogItem']['name']
            if name.lower() in target.lower():
                element = {'name': i['catalogItem']
                           ['name'], 'id': i['catalogItem']['id']}
                result.append(element)

        return result

    def get_catalogitem_byid(self, catalog_id):
        """Retrieves a specific catalog item by ID.

        :param catalog_id: A string containing the catalog ID you're looking for

        :return: A dictionary containing the response from the request
        """

        url = "https://%s/catalog-service/api/consumer/entitledCatalogItems?$filter=id eq '%s'" % (
            self.cloudurl, catalog_id)
        return self._request(url)

    def get_request_template(self, catalogitem):
        """Retrieves a request template from the API.

        The template will be stored in a python dictionary where values can
        be modified as needed.

        :param catalogitem: The UUID of the catalog item to retrieve a template for
        :return: A python dictionary representation of the JSON return from the API
        """

        url = 'https://%s/catalog-service/api/consumer/entitledCatalogItems/%s/requests/template' % (
            self.cloudurl, catalogitem)
        return self._request(url)

    def get_request_template_url(self, catalogitem):
        """Retrieves the URL for the template.

        :param catalogitem:
        :return:
        """

        url = 'https://%s/catalog-service/api/consumer/entitledCatalogItems/%s/requests/template' % (
            self.cloudurl, catalogitem)
        return url

    def get_request_url(self, catalogitem):
        """Retrieves the URL for making the request.

        :param catalogitem:

        :return:
        """

        url = 'https://%s/catalog-service/api/consumer/entitledCatalogItems/%s/requests' % (
            self.cloudurl, catalogitem)
        return url

    def request_item(self, catalogitem, payload=False):
        """Allows you to request an item from the vRealize catalog.

        Basic usage:

        Log into vra:
        vra = vralib.Session.login(username, password, cloudurl, tenant, ssl_verify=False)

        Submit a unique id to the method:

        build = vra.request_item('0ebbcf20-abdf-4663-a40c-1e50e7340190')

        There is an optional payload argument. Use this whenever you need to modify the request template prior to submission.

        For example you may opt to change the description of the catalog item with:

        payload = vra.get_request_template('0ebbcf20-abdf-4663-a40c-1e50e7340190')
        payload['description'] = 'My API test!'

        build = vra.request_item('0ebbcf20-abdf-4663-a40c-1e50e7340190', payload)

        See the docstring for the self.get_request_template() method for additional information

        :param catalogitem: A string that includes the unique ID of the catalog item to be provisioned
        :param payload: An optional parameter that should be a dictionary of the catalog request template which can be retrieved via the self.get_request_template method()
        :return: A python dictionary that includes the output from POST operation.

        """

        # TODO should make sure we can modify catalog item beforehand

        if not payload:
            payload = self.get_request_template(catalogitem)

        url = 'https://%s/catalog-service/api/consumer/entitledCatalogItems/%s/requests' % (
            self.cloudurl, catalogitem)
        return self._request(url, request_method="POST", payload=payload)

    def get_eventbroker_events(self):
        """Retrieves events from Event Broker.

        :return:
        """

        # TODO create a handler for the different API verbs this thing needs to support

        url = 'https://%s/event-broker-service/api/events' % self.cloudurl
        return self._iterate_pages(url)

    def get_requests(self):
        """Retrieves all requests.

        :return:
        """

        url = 'https://%s/catalog-service/api/consumer/requests' % self.cloudurl
        return self._iterate_pages(url)

    def get_request(self, request_id):
        """Retrieves a requests specified by request_id.

        param request_id:

        :return:
        """

        url = 'https://%s/catalog-service/api/consumer/requests/%s' % (
            self.cloudurl, request_id)
        return self._request(url)

    def get_requests_forms_details(self, resource_id):
        """Retrieves some request details on an individual request.

        May exclude later.

        :return:
        """

        url = 'https://%s/catalog-service/api/consumer/requests/%s' % (
            self.cloudurl, resource_id)
        return self._request(url)

    def get_request_details(self, request_id):
        """Retrieves details about a given request.

        Currently looks identical to output from get_requests_forms_details() method.

        :param id:

        :return:
        """

        url = 'https://%s/catalog-service/api/consumer/requests/%s/resourceViews' % (
            self.cloudurl, request_id)
        return self._request(url)

    def get_consumer_resources(self):
        """Retrieves a list of all the provisioned items.

        :return:
        """

        url = 'https://%s/catalog-service/api/consumer/resources' % self.cloudurl
        return self._iterate_pages(url)

    def get_consumer_resource(self, resource_id):
        """Retrieves a consumer resource by resource_id.

        :return:
        """

        url = 'https://%s/catalog-service/api/consumer/resources/%s' % (
            self.cloudurl, resource_id)
        return self._request(url)

    def get_reservations_info(self):
        """
        Retrieves all of the current reservations including allocation percentage and returns a dictionary.

        :return: A Python dictionary including all of the reservation information
        """

        url = 'https://%s/reservation-service/api/reservations/info' % self.cloudurl
        return self._request(url)

    def get_reservations(self):
        """Retrieves all of the current reservations and returns a dictionary.

        :return: A Python dictionary including all of the reservations
        """

        url = 'https://%s/reservation-service/api/reservations' % self.cloudurl
        return self._request(url)

    def get_reservation(self, reservation_id):
        """Retrieves a reservation details and returns a dictionary.

        :return: A Python dictionary including all of the reservation information for a specific reservation
        """

        url = 'https://%s/reservation-service/api/reservations/%s' % (
            self.cloudurl, reservation_id)
        return self._request(url)

    def new_reservation_from_existing(self, name, existing_reservation_id):
        """Creates a new reservation using an existing reservation as a template.

        :return: An empty response of b'' 
        """
        # TODO update to return JSON for newly created reservation on completion
        # TODO update to take input of desired assigned business group ID as well; currently assigns to whatever is in template; can't be modified

        url = 'https://%s/reservation-service/api/reservations' % self.cloudurl
        template = self._request(
            'https://%s/reservation-service/api/reservations/%s' % (self.cloudurl, existing_reservation_id))
        template['id'] = None
        template['name'] = name
        return self._request(url, request_method='POST', payload=template)

    def get_resource_view(self, resource_id):
        """Retrieves a resource view by resource_id.

        :return:
        """

        options = "?managedOnly=false&withExtenedData=true&withOperations=true"
        url = 'https://%s/catalog-service/api/consumer/resourceViews/%s%s' % (
            self.cloudurl, resource_id, options)
        return self._request(url)

# TODO build blueprints


# TODO look into what it would take to configure a business group with endpoints, reservation, etc.
#

class CatalogItem(object):
    pass
