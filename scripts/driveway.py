"""Shared concept driveway geometry; not a traffic-engineering certification."""

from dataclasses import dataclass
import math


FT = .3048


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        cross = (x - a[0]) * dy - (y - a[1]) * dx
        if abs(cross) < 1e-7 and min(a[0], b[0]) - 1e-7 <= x <= max(a[0], b[0]) + 1e-7 and min(a[1], b[1]) - 1e-7 <= y <= max(a[1], b[1]) + 1e-7:
            return True
        if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * dx / dy:
            inside = not inside
    return inside


def in_rect(point, rect):
    return rect[0] <= point[0] <= rect[0] + rect[2] and rect[1] <= point[1] <= rect[1] + rect[3]


def polygons_overlap(a, b):
    """Separating-axis test for convex footprints."""
    for polygon in (a, b):
        for p, q in zip(polygon, polygon[1:] + polygon[:1]):
            axis = (p[1] - q[1], q[0] - p[0])
            pa = [v[0] * axis[0] + v[1] * axis[1] for v in a]
            pb = [v[0] * axis[0] + v[1] * axis[1] for v in b]
            if min(max(pa), max(pb)) - max(min(pa), min(pb)) <= 1e-7:
                return False
    return True


def rect_polygon(rect):
    x, y, w, d = rect
    return [(x, y), (x + w, y), (x + w, y + d), (x, y + d)]


@dataclass(frozen=True)
class RoadPoint:
    x: float
    y: float
    z: float
    tx: float
    ty: float
    inner: float
    outer: float

    def offset(self, distance):
        return self.x + self.ty * distance, self.y - self.tx * distance


class Driveway:
    def __init__(self, spec):
        required = ["straight_ft", "radius_ft", "exit_ft", "clear_width_ft", "bend_outer_ft", "flare_ft"]
        if any(not finite(spec.get(key)) or spec[key] <= 0 for key in required):
            raise ValueError("Driveway dimensions must be finite positive feet")
        start = spec.get("start")
        grades = spec.get("grade_stations")
        if not isinstance(start, list) or len(start) != 2 or not all(finite(v) for v in start):
            raise ValueError("Driveway needs an explicit two-coordinate start")
        if not isinstance(grades, list) or len(grades) < 2 or any(
                not isinstance(row, list) or len(row) != 2 or not all(finite(v) for v in row) for row in grades):
            raise ValueError("Driveway needs finite station/gradient pairs")
        if grades[0] != [0, 0] or grades[-1][1] != 0 or any(
                b[0] <= a[0] or a[1] > 0 or b[1] > 0 for a, b in zip(grades, grades[1:])):
            raise ValueError("Driveway grades must start/end level and progress downhill")
        self.start = tuple(start)
        self.straight = spec["straight_ft"]
        self.radius = spec["radius_ft"]
        self.exit = spec["exit_ft"]
        self.half_width = spec["clear_width_ft"] / 2
        self.outer = spec["bend_outer_ft"]
        self.flare = spec["flare_ft"]
        self.grades = grades
        self.arc_end = self.straight + math.pi * self.radius / 2
        self.length = self.arc_end + self.exit
        if self.radius <= self.half_width or self.outer < self.half_width or self.flare > self.straight or grades[-1][0] > self.length:
            raise ValueError("Impossible driveway radius, widening or grade length")
        self.center = (start[0] - self.radius, start[1] + self.straight)

    def elevation(self, station):
        if not finite(station) or not 0 <= station <= self.length + 1e-7:
            raise ValueError("Driveway station outside its path")
        z = 0
        for a, b in zip(self.grades, self.grades[1:]):
            distance = min(station, b[0]) - a[0]
            if distance > 0:
                z += a[1] * distance + (b[1] - a[1]) * distance * distance / (2 * (b[0] - a[0]))
            if station <= b[0]:
                break
        return z

    def grade(self, station):
        self.elevation(station)
        for a, b in zip(self.grades, self.grades[1:]):
            if a[0] <= station <= b[0]:
                return a[1] + (b[1] - a[1]) * (station - a[0]) / (b[0] - a[0])
        return 0

    def at(self, station):
        z = self.elevation(station)
        if station <= self.straight:
            x, y = self.start[0], self.start[1] + station
            tx, ty = 0, 1
            t = max(0, (station - self.straight + self.flare) / self.flare)
        elif station <= self.arc_end:
            angle = (station - self.straight) / self.radius
            x = self.center[0] + self.radius * math.cos(angle)
            y = self.center[1] + self.radius * math.sin(angle)
            tx, ty = -math.sin(angle), math.cos(angle)
            t = 1
        else:
            x, y = self.center[0] - (station - self.arc_end), self.center[1] + self.radius
            tx, ty = -1, 0
            t = max(0, 1 - (station - self.arc_end) / self.exit)
        easing = t * t * (3 - 2 * t)
        return RoadPoint(x, y, z, tx, ty, self.half_width, self.half_width + (self.outer - self.half_width) * easing)

    def stations(self, step=.5):
        if not finite(step) or step <= 0:
            raise ValueError("Driveway sample spacing must be positive")
        count = math.ceil(self.length / step)
        return sorted({*(self.length * i / count for i in range(count + 1)),
                       *(row[0] for row in self.grades), self.straight - self.flare, self.straight, self.arc_end})

    def sections(self, step=.5):
        return [self.at(s) for s in self.stations(step)]

    def polygon(self, step=.5):
        sections = self.sections(step)
        return [p.offset(-p.inner) for p in sections] + [p.offset(p.outer) for p in reversed(sections)]

    def station_at(self, point):
        x, y = point
        straight = min(self.straight, max(0, y - self.start[1]))
        angle = min(math.pi / 2, max(0, math.atan2(y - self.center[1], x - self.center[0])))
        arc = self.straight + self.radius * angle
        exit_station = self.arc_end + min(self.exit, max(0, self.center[0] - x))
        return min([straight, arc, exit_station], key=lambda s: (self.at(s).x - x) ** 2 + (self.at(s).y - y) ** 2)

    def vehicle_footprint(self, station, vehicle, clearance=True):
        p = self.at(station)
        margin = vehicle["clearance_m"] / FT if clearance else 0
        half = vehicle["width_m"] / (2 * FT) + margin
        rear = -vehicle["rear_overhang_m"] / FT - margin
        front = (vehicle["wheelbase_m"] + vehicle["front_overhang_m"]) / FT + margin
        return [(p.x + p.tx * u + p.ty * v, p.y + p.ty * u - p.tx * v)
                for u, v in [(rear, -half), (front, -half), (front, half), (rear, half)]]


def check_vehicle(vehicle):
    keys = ["length_m", "width_m", "height_m", "wheelbase_m", "front_overhang_m",
            "rear_overhang_m", "clearance_m", "ground_clearance_m", "minimum_rear_radius_m"]
    if any(not finite(vehicle.get(key)) or vehicle[key] <= 0 for key in keys):
        raise ValueError("Design vehicle needs explicit positive metre dimensions")
    if not math.isclose(vehicle["length_m"], sum(vehicle[k] for k in ["wheelbase_m", "front_overhang_m", "rear_overhang_m"]), abs_tol=1e-6):
        raise ValueError("Vehicle overhangs and wheelbase must add up to its length")


def vertical_clearances(road, vehicle, overhead):
    wb = vehicle["wheelbase_m"] / FT
    finish = overhead["finish_ft"]
    minimum_roof = minimum_underbody = math.inf
    for station in road.stations(1):
        p = road.at(station)
        front = (p.x + p.tx * wb, p.y + p.ty * wb)
        rear_z = p.z + finish
        front_z = road.elevation(road.station_at(front)) + finish
        slope = (front_z - rear_z) / wb
        rear = -vehicle["rear_overhang_m"] / FT
        reach = (vehicle["wheelbase_m"] + vehicle["front_overhang_m"]) / FT
        for i in range(21):
            u = rear + (reach - rear) * i / 20
            center = (p.x + p.tx * u, p.y + p.ty * u)
            if center[1] < road.start[1]:
                continue
            surface = road.elevation(road.station_at(center)) + finish
            minimum_underbody = min(minimum_underbody, (rear_z + slope * u - surface) * FT + vehicle["ground_clearance_m"])
            for side in [-1, 1]:
                half = side * vehicle["width_m"] / (2 * FT)
                point = (center[0] + p.ty * half, center[1] - p.tx * half)
                cover = overhead["slab_under_ft"] if in_rect(point, overhead["basement_cover_rect"]) else overhead["canopy_under_ft"]
                roof = rear_z + slope * u + vehicle["height_m"] / FT
                minimum_roof = min(minimum_roof, (cover - roof) * FT)
    return minimum_roof, minimum_underbody


def sweep_report(spec, aisle, obstacles, site, portal, overhead=None):
    road = Driveway(spec)
    vehicle = spec["design_vehicle"]
    check_vehicle(vehicle)
    polygon = road.polygon()
    errors = []
    if road.radius * FT < vehicle["minimum_rear_radius_m"]:
        errors.append("Driveway bend is tighter than the design rear-axle radius")
    if any(not in_rect(p, site) for p in polygon):
        errors.append("Driveway pavement extends outside the study plot")
    if abs(road.elevation(road.length) - spec["basement_elevation_ft"]) > 1e-6:
        errors.append("Driveway finished profile does not meet the basement level")
    crossing = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if min(a[0], b[0]) <= portal["at"] <= max(a[0], b[0]) and abs(a[0] - b[0]) > 1e-9:
            t = (portal["at"] - a[0]) / (b[0] - a[0])
            crossing.append(a[1] + t * (b[1] - a[1]))
    if not crossing or min(crossing) < portal["start"] - 1e-6 or max(crossing) > portal["start"] + portal["width"] + 1e-6:
        errors.append("Garage portal clips the swept driveway pavement")
    samples = road.stations(.5)
    collision_stations = []
    for s in samples:
        body = road.vehicle_footprint(s, vehicle)
        boundary = []
        for a, b in zip(body, body[1:] + body[:1]):
            boundary += [(a[0] + (b[0] - a[0]) * t / 4, a[1] + (b[1] - a[1]) * t / 4) for t in range(5)]
        if any(p[1] >= site[1] and not (point_in_polygon(p, polygon) or in_rect(p, aisle)) for p in boundary):
            collision_stations.append(s)
        if any(polygons_overlap(body, rect_polygon(rect)) for rect in obstacles):
            errors.append(f"Vehicle body/clearance hits parked furniture near station {s:.2f} ft")
            break
    if collision_stations:
        errors.append(f"Vehicle body/overhang clearance leaves the pavement near station {collision_stations[0]:.2f} ft")
    straight_grade = max(abs(road.grade(s)) for s in samples if s <= road.straight)
    curved_grade = max(abs(road.grade(s)) for s in samples if road.straight <= s <= road.arc_end)
    if straight_grade > .14 + 1e-8 or curved_grade > .10 + 1e-8:
        errors.append("Driveway exceeds the candidate 14% straight / 10% curved grade limits")
    report = {
        "status": "FAIL" if errors else "PASS", "errors": errors,
        "samples": len(samples), "path_length_ft": road.length,
        "straight_max_grade": straight_grade, "curve_max_grade": curved_grade,
        "minimum_rear_axle_radius_m": road.radius * FT,
        "body_clearance_m": vehicle["clearance_m"],
        "portal_span_ft": [min(crossing), max(crossing)] if crossing else [],
        "scope": "Sampled low-speed design-vehicle geometry only; street approach, traction, drainage, structures and legal compliance are not certified",
    }
    if overhead is not None:
        roof, underside = vertical_clearances(road, vehicle, overhead)
        if roof < vehicle["clearance_m"]:
            errors.append(f"Vehicle roof clearance is only {roof:.3f} m")
        if underside < .1:
            errors.append(f"Vehicle underside clearance is only {underside:.3f} m")
        report.update({"minimum_roof_clearance_m": roof, "minimum_underbody_clearance_m": underside,
                       "overhead_assumptions": overhead, "status": "FAIL" if errors else "PASS"})
    return report
