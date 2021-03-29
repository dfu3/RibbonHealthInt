import json
import collections
import csv


class ProviderCollection(object):

    def __init__(self, logs, original):
        self.records = self._json_to_dict(original)
        self.log_file = logs

    def _json_to_dict(self, file):
        records = []
        with open(file, 'r') as file:
            data = file.read()
            records = json.loads(data, object_pairs_hook=collections.OrderedDict)  # keep original order
            for rec in records:  # this will speed up the lookup for removing items
                rec['insurances'] = set(rec['insurances'])
                rec['locations'] = set(rec['locations'])
                rec['specialties'] = set(rec['specialties'])
        record_map = {item['npi']: item for item in records}  # nobody wants that O(n) lookup
        return record_map

    def write_to_file(self):
        for rec in self.records.values():
            rec['insurances'] = list(rec['insurances'])
            rec['locations'] = list(rec['locations'])
            rec['specialties'] = list(rec['specialties'])
        with open("final_records.json", "w") as outfile:
            json.dump(list(self.records.values()), outfile)

    def add(self, npi, field, obj):  # adds new obj to the target field
        self.records[npi][field].add(obj)

    def remove(self, npi, field, obj):  # removes obj if exists in field
        self.records[npi][field].discard(obj)

    def override(self, npi, field, obj):  # replaces all objects in field with given object
        self.records[npi][field] = {obj}

    def update_custom(self, npi, field, obj):  # update with custom field and value
        self.records[npi][field] = obj

    def remove_custom(self, npi, field):  # deletes custom field if exists
        del self.records[npi][field]

    def process_logs(self):
        with open(self.log_file, 'r') as file:
            for line in reversed(list(csv.reader(file))):
                if line[0] == 'npi':  # ignore headers
                    break

                npi, path, meth, req, ts = line
                req = json.loads(req)
                parts = path.split('/')
                key = next(iter(req))
                val = req[key]

                if len(parts) == 6:  # stock fields
                    attr = parts[-1]
                    for obj in val:
                        getattr(self, key)(npi, attr, obj)  # calls method by name based on action
                elif len(parts) == 5:  # custom fields
                    if key == 'remove_fields':
                        for obj in req['remove_fields']:  # loop to ignore empty list of fields
                            self.remove_custom(npi, obj)
                    else:
                        self.update_custom(npi, key, val)


if __name__ == '__main__':
    instance = ProviderCollection('client_logs.csv', 'original_records.json')
    instance.process_logs()
    instance.write_to_file()