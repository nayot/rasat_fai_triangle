from geopy.distance import geodesic

class GeoLogic:
    @staticmethod
    def calculate_distance(p1, p2):
        return geodesic(p1, p2).km

    def check_fai_threshold(self, v1, v2, v3):
        d1 = self.calculate_distance(v1, v2)
        d2 = self.calculate_distance(v2, v3)
        d3 = self.calculate_distance(v3, v1)
        side_lengths = [d1, d2, d3]
        total_dist = sum(side_lengths)
        # กฎด้านสั้นที่สุดต้องไม่น้อยกว่า 28% [cite: 8, 13]
        is_fai = min(side_lengths) >= (total_dist * 0.28)
        return is_fai, total_dist

    def is_within_radius(self, p1, p2, radius_meters):
        return (self.calculate_distance(p1, p2) * 1000) <= radius_meters