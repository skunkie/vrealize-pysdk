# vrealize-pysdk

This repository stores tools and and an SDK for VMware's vRealize Automation.

## Overview

A basic vRealize automation wrapper API called vralib.

The library has the following dependencies:

* requests

## Sample Scripts

In the 'tool-samples' directory you'll find a series of helpful but simples tools that leverage this API to give you an idea of usage.

* tool-samples/get-apiurls.py - Collects the API URLs with JSON templates to assist in API integration,
* tool-samples/get-catalog.py - Returns a prettytable formatted list of catalog names and IDs. The IDs can be used to request resources,
* tool-samples/get-items.py - A script to pull a list of provisioned items,
* tool-samples/report-roles.py - A script to create a report of all the users and assigned roles in a given tenant,
* tool-samples/request-item.py - A script to request a vRA catalog item.

To run the tools, install dependencies:
    pip install -r ./requirements.txt

## Setup 

Use pip to install the package:

    pip install ./vrealize-pysdk.tar.gz

## Usage

### Log into the vRA instance

Import the library:

    import vralib

Use the vralib.Session.login() method to log into the vRealize automation server by creating an object with the .login @classmethod:

    vra = vralib.Session.login(username, password, cloudurl, tenant, ssl_verify=False)
    
Variables are defined as:
* username - a string containing the username that's logging into the environment. Typically it's user@domain
* password - a string containing the password for the specified user. 
* cloudurl - a string that contains the FQDN or IP address of the vrealize automation server. Don't include the https bit. The library will sort out specific URLs for you
* tenant - an optional string that contains the tenant you want to log into. If you leave this blank it will log into the default tenant
* ssl_verify - a boolean value that can be used to disable SSL verification. Helpful for when you don't have signed/trusted certificates (like a development environment) 

### Getting data from the API

Once logged in you can access various methods through the object `vra`.

#### Examples

Get all business groups the user is a group manager of. This is not avalable for ordinary users:

    business_groups = vra.get_business_groups()

Get all catalog items the user is entitled to:

    catalog_items = vra.get_entitled_catalog_items()

Get a catalog item by name 'cent':

    catalog_item = vra.get_catalogitem_byname('cent')

# Contributions welcome!
