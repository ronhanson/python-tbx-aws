#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
"""
:Author: Ronan Delacroix
:Copyright: (c) 2018 Ronan Delacroix
"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
"""
:Author: Ronan Delacroix
:Copyright: (c) 2018 Ronan Delacroix
"""
import os
import boto3
import requests


class EC2:


    def __init__(self, region=None):
        self.__instance_metadata = None
        self.__instance_object = None
        if not region:
            region = self.current_region
        self.ec2 = boto3.resource('ec2', region_name=region)

    def current_instance_metadata(self):
        if not self.__instance_metadata:
            r = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document")
            r.raise_for_status()
            self.__instance_metadata = r.json()
        return self.__instance_metadata

    @property
    def current_instance_id(self):
        return self.current_instance_metadata().get('instanceId')

    @property
    def current_region(self):
        return self.current_instance_metadata().get('region')


    def reload(self):
        self.__instance_metadata = None
        self.__instance_object = None
        return self.current_instance


    def instance(self, id=None):
        instance_id = id
        if not id:
            instance_id = self.current_instance_id
        if not instance_id:
            raise Exception('Invalid instance_id: {}'.format(instance_id))
        instance = self.ec2.Instance(instance_id)
        if not id:
            self.__instance_object = instance
        return instance


    def current_instance(self):
        return self.instance()


    def get_instance_tags(self, instance=None):
        if not instance:
            instance = self.current_instance()
        tags = instance.tags or []
        return {t.get('Key'): t.get('Value') for t in tags}


    def get_instance_name(self, instance=None):
        return self.instance_tags(instance).get('Name')


    def get_instances_by_tags(self, tags={}):
        all_instances = self.ec2.instances.all()
        found_instances = []
        for instance in all_instances:
            instance_tags = self.get_instance_tags(instance)
            found = True
            for k, v in tags.items():
                if not(k in instance_tags and instance_tags.get(k) == v):
                    found = False
                    break
            if found:
                found_instances.append(instance)
        return found_instances


    def create_tags(self, instance=None, tags={}):
        if not instance:
            instance = self.current_instance()
        if tags:
            tags = [{'Key': key, 'Value': value} for key, value in tags.items()]
            instance.create_tags(Tags=tags)
            instance.reload()
        return instance


    def delete_tags(self, instance=None, tags=[]):
        if not instance:
            instance = self.current_instance()
        if tags:
            tags = [{'Key': key} for key in tags]
            instance.delete_tags(Tags=tags)
            instance.reload()
        return instance


class Route53:

    def __init__(self):
        self.r53 = boto3.client('route53')


    def list_hosted_zones(self):
        return self.r53.list_hosted_zones().get('HostedZones')


    def get_zone(self, name):
        if name[-1]!='.':
            name = name+"."
        zone = [z for z in self.list_hosted_zones() if z.get('Name') == name]
        if not zone:
            return None
        return zone[0]


    def get_zone_id(self, zone=None, name=None):
        if (not zone) and name:
            zone = self.get_zone(name)
        if not zone:
            return None
        return zone.get('Id').replace('/hostedzone/', '')


    def list_records(self, zone_id):
        return self.r53.list_resource_record_sets(HostedZoneId=zone_id).get("ResourceRecordSets")


    def create_record(self, zone_id, source, target, type='A', ttl=300):
        if type(target) is list:
            targets = [{'Value' : v} for v in target]
            targets_str = ' + '.join(target)
        else:
            targets = [{'Value': target}]
            targets_str = target
        return self.r53.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch= {
                'Comment': 'add %s -> %s' % (source, targets_str),
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': source,
                            'Type': type,
                            'TTL': ttl,
                            'ResourceRecords': targets
                        }
                    }
                ]
            }
        )


    def delete_record(self, zone_id, source):
        if source[-1] != '.':
            source = source + '.'

        matching_records = [r for r in self.list_records(zone_id=zone_id) if r.get('Name') == source]

        if matching_records:
            matching_records = matching_records[0]
            type = matching_records.get('Type')
            values = matching_records.get('ResourceRecords')
            ttl = matching_records.get('TTL')
            return self.r53.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch= {
                    'Changes': [
                        {
                            'Action': 'DELETE',
                            'ResourceRecordSet': {
                                'Name': source,
                                'Type': type,
                                'TTL': ttl,
                                'ResourceRecords': values
                            }
                        }
                    ]
                }
            )
        return None
