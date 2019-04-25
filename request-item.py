#!/usr/bin/env python

"""

    vRA Request Tool. A tool I use to build VMs for the purposes of running some tests. 

"""

__version__ = "$Revision"

import getpass
import argparse
import json
import six
import time

import vralib

from pprint import pprint
from vralib.vraexceptions import NotFoundError


def getargs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server',
                        required=True,
                        action='store',
                        help='FQDN of the Cloud Provider.')
    parser.add_argument('-u', '--username',
                        required=False,
                        action='store',
                        help='Username to access the cloud provider')
    parser.add_argument('-t', '--tenant',
                        required=True,
                        action='store',
                        help='vRealize tenant')
    parser.add_argument('-b', '--businessgroup',
                        required=True,
                        action='store',
                        help='The full name of the business group')
    parser.add_argument('-c', '--catalogitem',
                        required=True,
                        action='store',
                        help='The partial or full name of the catalog item you want the ID for')
    parser.add_argument('-r', '--reasons',
                        required=True,
                        action='store',
                        help='The reason for the requested item. Enclose in quotes.')
    parser.add_argument('-d', '--description',
                        required=False,
                        action='store',
                        help='An optional description for the requested resource. Enclose in quotes.')
    parser.add_argument('-p', '--parameters',
                        required=False,
                        action='store',
                        help='The path to optional parameters for the requested resource in JSON format.')
    args = parser.parse_args()
    return args


def patch_dict(d, p):
    for k in p:
        if k in d.keys():
            if type(d[k]) == dict:
                d[k] = patch_dict(d[k], p[k])
            else:
                d[k] = p[k]
    return d


def main():
    args = getargs()
    cloudurl = args.server
    username = args.username
    tenant = args.tenant
    if not username:
        username = six.moves.input('vRA Username (user@domain): ')
    password = getpass.getpass('vRA Password: ')
    vra = vralib.Session.login(username, password, cloudurl,
                               tenant, ssl_verify=False)

    business_group = vra.get_businessgroup_byname(args.businessgroup)
    if not business_group:
        raise NotFoundError("Business Group %s is not found, exiting" % args.businessgroup)
    if len(business_group) > 1:
        raise Exception("Found %d Business Groups for %s, exiting" % (len(business_group), args.businessgroup))

    request_template = vra.get_request_template(catalogitem=args.catalogitem)

    request_template['businessGroupId'] = business_group[0]['id']
    if args.description:
        request_template['description'] = args.description
    if args.reasons:
        request_template['reasons'] = args.reasons

    if args.parameters:
        fd = open(args.parameters, 'r')
        d = json.loads(fd.read())
        fd.close()
        request_template = patch_dict(request_template, d)

    # request_template['data']['inputServices'] = ["application-2b47b67a-7563-41df-bc9a-b01374210cad"]
    # request_template['data']['defaultSectionId'] = "d69e3a00-6cd9-4832-b7ba-0498b17acda4"
    # request_template['data']['inputSources'] = ["securitygroup-bf4bda4c-fc17-4935-a635-7562d1b36cf0"]
    # request_template['data']['inputDestinations'] = ["securitygroup-bf4bda4c-fc17-4935-a635-7562d1b36cf0"]
    # request_template['data']['ruleName'] = "vra-service-test001"

    pprint(request_template, indent=4)

    # TODO add some logic to query for options here.
    # TODO should be noted that this only changes one custom property. Need to design some logic to extend this
    # request_template['data']['Linux_vSphere_VM']['data']['Puppet.RoleClass'] = "role::linux_mysql_database"

    build_vm = vra.request_item(catalogitem=args.catalogitem,
                                payload=request_template)

    while True:
        vra_request = vra.get_request(request_id=build_vm['id'])
        print('Current provisioning state is:', vra_request['stateName'],
              'Current phase is:', vra_request['phase'])
        if vra_request['state'] == 'PROVIDER_FAILED':
            raise Exception('Request provider failed! Dumping JSON output of request',
                            pprint(vra_request, indent=4))
        elif vra_request['state'] == 'FAILED':
            raise Exception('Failed inside of vRA! Dumping JSON output of request',
                            pprint(vra_request, indent=4))
        elif vra_request['state'] == 'SUCCESSFUL':
            break
        time.sleep(5)

    print("#" * 80)
    pprint(vra_request, indent=4)


if __name__ == '__main__':
    main()
