# threat_assessment/threat_assessment.py

import math
from collections import defaultdict

class ThreatAssessment:
    def __init__(self):
        # Default threat coefficients for each object type
        self.threat_coefficients = {
            "Human": 1.0,
            "Drone": 2.0,
            "Helicopter": 3.0,
            "Missile": 5.0,
            "Missile Launchers": 4.5,
            "Aircraft": 3.5,
            "Tank": 4.0,
            "Truck": 2.5,
            "Warship": 4.5,
            "Weapon": 3.0,
            "Unknown": 1.0,
        }

        # Maximum threat levels for each object type to prevent exaggeration
        self.max_threat_levels = {
            "Human": 100.0,
            "Drone": 100.0,
            "Helicopter": 100.0,
            "Missile": 100.0,
            "Missile Launchers": 100.0,
            "Aircraft": 100.0,
            "Tank": 100.0,
            "Truck": 100.0,
            "Warship": 100.0,
            "Weapon": 100.0,
            "Unknown": 100.0,
        }

    def perform_threat_assessment(self, app):
        # Retrieve currently tracked objects from the video processor
        tracked_objects = app.video_processor.current_tracked_objects

        # Create a dictionary to store object details
        objects = {}
        for obj in tracked_objects:
            track_id = str(obj['track_id'])
            cls = obj['cls']
            bbox = obj['bbox']  # [x1, y1, x2, y2]
            status_info = app.object_statuses.get(track_id, {'status': 'Unknown', 'selected': False})
            status = status_info.get('status', 'Unknown')
            objects[track_id] = {
                'class': cls,
                'bbox': bbox,
                'status': status,
                'threat_level': 0.0
            }

        # Precompute group centers for friends and enemies
        friend_objects = [obj for obj in objects.values() if obj['status'] == 'friend']
        enemy_objects = [obj for obj in objects.values() if obj['status'] == 'adversary']

        friend_centers = self.get_group_centers(friend_objects)
        enemy_centers = self.get_group_centers(enemy_objects)

        # Base threat calculation
        for obj in objects.values():
            cls = obj['class']
            status = obj['status']
            base_coeff = self.threat_coefficients.get(cls, self.threat_coefficients["Unknown"])
            
            if status == 'friend':
                multiplier = 0
            elif status == 'adversary':
                multiplier = 3
            else:
                multiplier = 1
            
            base_threat = base_coeff * multiplier
            obj['threat_level'] = base_threat

        # Apply proximity rules
        for enemy_id, enemy in objects.items():
            if enemy['status'] != 'adversary':
                continue  # Only consider enemies for threat adjustments

            enemy_bbox = enemy['bbox']

            # 1. Distance to friends
            for friend_id, friend in objects.items():
                if friend['status'] != 'friend':
                    continue
                distance = self.calculate_distance(enemy_bbox, friend['bbox'])
                if distance < 400:
                    if 300 <= distance < 400:
                        enemy['threat_level'] += 2
                    elif 200 <= distance < 300:
                        enemy['threat_level'] += 4
                    elif 100 <= distance < 200:
                        enemy['threat_level'] += 6
                    elif 0 <= distance < 100:
                        enemy['threat_level'] += 10

            # 2. Group proximity
            for friend_center in friend_centers:
                for enemy_center in enemy_centers:
                    distance_between_centers = self.euclidean_distance(friend_center, enemy_center)
                    if distance_between_centers < 500:
                        enemy['threat_level'] *= 2.5
                        break  # Apply multiplier once per group

            # 3. Proximity to other threats
            for other_id, other in objects.items():
                if other_id == enemy_id:
                    continue
                if other['status'] not in ['friend', 'adversary']:
                    continue
                distance = self.calculate_distance(enemy_bbox, other['bbox'])
                if distance < 100:
                    enemy['threat_level'] *= 2

        # 4. Unknown objects near enemies
        for obj_id, obj in objects.items():
            if obj['status'] != 'Unknown':
                continue
            for enemy in enemy_objects:
                distance = self.calculate_distance(obj['bbox'], enemy['bbox'])
                if distance < 300:
                    obj['threat_level'] *= 2
                    break  # Apply multiplier once if close to any enemy

        # 5. Cap threat levels
        for obj in objects.values():
            cls = obj['class']
            max_threat = self.max_threat_levels.get(cls, 10.0)
            obj['threat_level'] = self.clamp(obj['threat_level'], 0, max_threat)

        # Update threat levels in the application
        for track_id, obj in objects.items():
            app.object_statuses.setdefault(track_id, {'status': 'Unknown', 'selected': False})
            app.object_statuses[track_id]['threat_level'] = obj['threat_level']

    def calculate_distance(self, bbox1, bbox2):
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2

        # If bounding boxes overlap, distance is zero
        if (x1_min <= x2_max and x1_max >= x2_min and
            y1_min <= y2_max and y1_max >= y2_min):
            return 0

        # Calculate horizontal and vertical distances
        dx = max(x2_min - x1_max, x1_min - x2_max, 0)
        dy = max(y2_min - y1_max, y1_min - y2_max, 0)

        return math.hypot(dx, dy)

    def euclidean_distance(self, point1, point2):
        return math.hypot(point1[0] - point2[0], point1[1] - point2[1])

    def get_group_centers(self, objects):
        centers = []
        for obj in objects:
            bbox = obj['bbox']
            x1, y1, x2, y2 = bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            centers.append((center_x, center_y))
        return centers

    def clamp(self, value, min_value, max_value):
        return max(min_value, min(value, max_value))