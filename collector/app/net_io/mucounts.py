import json


class MUCounts:
    """
    Class object that represent a MonitorUnit Update message. Implement all function to extract/create Json object fields
    """
    def __init__(self, json_data=None):
        """
        Create a new instance of Counts-Update object
        :param json_data:
        """
        self.entrances = []
        self.exits = []
        self.device_id = ''
        if json_data is not None:
            self.load(json_data)

    def load(self, j_data):
        """
        Extract all Json-Fields containing Entrances/Exits estimations sent from MUs
        :param j_data: Json object Update
        :return:
        """
        if not ('entrances' in j_data):
            raise Exception('NO entrances field in JSON')
        if not ('exits' in j_data):
            raise Exception('NO exits field in JSON')
        if not ('device_id' in j_data):
            raise Exception('NO device_id field in JSON')

        self.device_id = j_data['device_id']

        for e in j_data['entrances']:
            self.entrances.append((e[0], e[1]))

        for e in j_data['exits']:
            self.exits.append((e[0], e[1]))

    def jsonify(self):
        """
        :return: Json representation of `this`
        """
        obj_d = {'device_id': self.device_id, 'entrances': self.entrances, 'exits': self.exits}
        obj_j = json.dumps(obj_d)
        return obj_j
