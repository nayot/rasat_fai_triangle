class IGCParser:
    def __init__(self, file_path):
        self.file_path = file_path

    def parse(self):
        points = []
        with open(self.file_path, 'r') as f:
            for line in f:
                if line.startswith('B'):
                    lat = self._to_dec(line[7:15], True)
                    lon = self._to_dec(line[15:24], False)
                    alt = int(line[25:30])
                    time = line[1:7]
                    points.append((lat, lon, alt, time))
        return points

    def _to_dec(self, raw, is_lat):
        d = int(raw[0:2]) if is_lat else int(raw[0:3])
        m = int(raw[2:7])/1000 if is_lat else int(raw[3:8])/1000
        dec = d + (m/60)
        return -dec if raw[-1] in ['S', 'W'] else dec