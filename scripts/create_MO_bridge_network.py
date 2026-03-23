from __future__ import annotations

import argparse
import math
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import matplotlib
import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

SHOW_FLAG = "--show" in sys.argv
if not SHOW_FLAG:
    matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "Arial"

import matplotlib.pyplot as plt

from bridgesnet.config import TeamConfig
from bridgesnet.graph import node_colors, node_labels
from bridgesnet.plots import plot_network

BridgeRow = dict[str, object]
WorkbookRows = list[BridgeRow]


COUNTY_TOWN_DEFAULTS: dict[str, list[tuple[str, float, float]]] = {
    "BOONE": [
        ("Columbia", 38.9517, -92.3341),
        ("Ashland", 38.7742, -92.2574),
        ("Centralia", 39.2109, -92.1377),
    ],
    "JACKSON": [
        ("Kansas City", 39.0997, -94.5786),
        ("Independence", 39.0911, -94.4155),
        ("Lee's Summit", 38.9108, -94.3822),
        ("Blue Springs", 39.0169, -94.2816),
    ],
    "GREENE": [
        ("Springfield", 37.2089, -93.2923),
        ("Republic", 37.1206, -93.4808),
        ("Willard", 37.3051, -93.4277),
    ],
    "CLAY": [
        ("Liberty", 39.2461, -94.4191),
        ("Gladstone", 39.2039, -94.5544),
        ("North Kansas City", 39.1420, -94.5736),
        ("Kearney", 39.3681, -94.3611),
    ],
    "ST. LOUIS": [
        ("Clayton", 38.6426, -90.3237),
        ("Chesterfield", 38.6631, -90.5771),
        ("Florissant", 38.7892, -90.3226),
        ("Kirkwood", 38.5834, -90.4068),
    ],
    "ST. CHARLES": [
        ("St. Charles", 38.7881, -90.4974),
        ("St. Peters", 38.7875, -90.6299),
        ("O'Fallon", 38.8106, -90.6998),
        ("Wentzville", 38.8114, -90.8529),
    ],
    "COLE": [
        ("Jefferson City", 38.5767, -92.1735),
        ("Russellville", 38.5070, -92.4366),
        ("St. Martins", 38.5962, -92.2066),
    ],
    "PLATTE": [
        ("Platte City", 39.3706, -94.7825),
        ("Parkville", 39.1940, -94.6819),
        ("Riverside", 39.1733, -94.6138),
        ("Weston", 39.4128, -94.9014),
    ],
    "BUCHANAN": [
        ("St. Joseph", 39.7675, -94.8467),
        ("Easton", 39.7417, -94.6641),
        ("Agency", 39.6447, -94.7411),
    ],
    "CAPE GIRARDEAU": [
        ("Jackson", 37.3823, -89.6662),
        ("Cape Girardeau", 37.3059, -89.5181),
        ("Delta", 37.1803, -89.7340),
    ],
    "CASS": [
        ("Harrisonville", 38.6533, -94.3486),
        ("Belton", 38.8128, -94.5319),
        ("Raymore", 38.8017, -94.4527),
    ],
    "CHRISTIAN": [
        ("Ozark", 37.0209, -93.2063),
        ("Nixa", 37.0434, -93.2944),
        ("Clever", 37.0300, -93.4702),
    ],
    "FRANKLIN": [
        ("Union", 38.4470, -91.0085),
        ("Washington", 38.5581, -91.0121),
        ("Pacific", 38.4817, -90.7418),
        ("Sullivan", 38.2081, -91.1604),
    ],
    "JEFFERSON": [
        ("Hillsboro", 38.2314, -90.5629),
        ("Arnold", 38.4328, -90.3776),
        ("Festus", 38.2209, -90.3954),
    ],
    "ST. FRANCOIS": [
        ("Farmington", 37.7809, -90.4218),
        ("Park Hills", 37.8545, -90.5193),
        ("Bonne Terre", 37.9239, -90.5557),
    ],
    "PHELPS": [
        ("Rolla", 37.9514, -91.7713),
        ("St. James", 38.0017, -91.6149),
        ("Newburg", 37.9167, -91.9010),
    ],
    "TANEY": [
        ("Forsyth", 36.6851, -93.1182),
        ("Branson", 36.6437, -93.2185),
        ("Hollister", 36.6162, -93.2151),
    ],
    "NEWTON": [
        ("Neosho", 36.8701, -94.3674),
        ("Joplin", 37.0842, -94.5133),
        ("Seneca", 36.8445, -94.6111),
    ],
    "JASPER": [
        ("Carthage", 37.1764, -94.3102),
        ("Joplin", 37.0842, -94.5133),
        ("Webb City", 37.1464, -94.4630),
    ],
    "ST. LOUIS CITY": [
        ("St. Louis", 38.6270, -90.1994),
        ("Downtown West", 38.6312, -90.2059),
        ("Carondelet", 38.5514, -90.2418),
    ],
}


@dataclass(frozen=True)
class DepotSelection:
    county: str
    display_name: str
    latitude: float
    longitude: float


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Missouri bridge network from local bridge data"
    )
    _ = parser.add_argument(
        "--graph-file",
        type=Path,
        default=PROJECT_ROOT
        / "Missouri-Bridges-Data-Graphs"
        / "missouri_bridge_graph.pkl",
        help="Path to the Missouri bridge NetworkX pickle graph",
    )
    _ = parser.add_argument(
        "--workbook-file",
        type=Path,
        default=PROJECT_ROOT / "Missouri-Bridges-Data-Graphs" / "MOpoorbridges.xlsx",
        help="Path to MO poor bridges Excel workbook",
    )
    _ = parser.add_argument(
        "--output-graph",
        type=Path,
        default=PROJECT_ROOT / "results" / "mo_bridge_network.pkl",
        help="Output path for generated directed bridge network pickle",
    )
    _ = parser.add_argument(
        "--output-plot",
        type=Path,
        default=PROJECT_ROOT / "results" / "mo_bridge_network.pdf",
        help="Output path for generated network visualization",
    )
    _ = parser.add_argument(
        "--show",
        action="store_true",
        help="Display the plot in an interactive window",
    )
    return parser


def _to_float(value: object, default: float) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        parsed = float(str(value))
        if math.isnan(parsed):
            return default
        return parsed
    except (TypeError, ValueError):
        return default


def _normalize_text(value: object) -> str:
    return str(value).strip()


def _normalize_county(value: object) -> str:
    return _normalize_text(value).upper()


def _normalize_bridge_id(value: object) -> str:
    return _normalize_text(value)


def _normalize_bfi(minimum_rating: float) -> float:
    if minimum_rating <= 1.0:
        normalized = minimum_rating
    else:
        normalized = minimum_rating / 9.0
    return max(0.0, min(1.0, normalized))


def _derive_due_date(bfi: float) -> int:
    return 2 + int(round(bfi * 4))


def _distance_m_to_time_hours(distance_m: float, speed_kmh: float = 80.0) -> float:
    if distance_m <= 0:
        return 0.01
    return max((distance_m / 1000.0) / speed_kmh, 0.01)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_missouri_graph(graph_file: Path) -> nx.Graph[str]:
    if not graph_file.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_file}")

    with graph_file.open("rb") as file_obj:
        graph = pickle.load(file_obj)
    if not isinstance(graph, nx.Graph):
        raise TypeError("Loaded object is not a NetworkX graph")
    return cast("nx.Graph[str]", graph)


def _read_xlsx_rows(workbook_file: Path) -> WorkbookRows:
    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    def column_index(cell_ref: str) -> int:
        letters = "".join(character for character in cell_ref if character.isalpha())
        index = 0
        for character in letters:
            index = index * 26 + (ord(character.upper()) - 64)
        return max(index - 1, 0)

    with ZipFile(workbook_file) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for shared_item in shared_root.findall("a:si", namespace):
                text = "".join(
                    node.text or ""
                    for node in shared_item.iterfind(".//a:t", namespace)
                )
                shared_strings.append(text)

        worksheet_root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows: list[list[object | None]] = []
    for row in worksheet_root.findall(".//a:sheetData/a:row", namespace):
        row_values: list[object | None] = []
        current_index = 0
        for cell in row.findall("a:c", namespace):
            ref = cell.attrib.get("r", "")
            target_index = column_index(ref)
            while current_index < target_index:
                row_values.append(None)
                current_index += 1

            value_node = cell.find("a:v", namespace)
            if value_node is None:
                cell_value: object | None = None
            elif cell.attrib.get("t") == "s":
                cell_value = shared_strings[int(value_node.text or "0")]
            else:
                cell_value = value_node.text
            row_values.append(cell_value)
            current_index += 1
        rows.append(row_values)

    if not rows:
        raise ValueError("Workbook does not contain any rows")

    headers = [_normalize_text(value) for value in rows[0]]
    data_rows: WorkbookRows = []
    for raw_row in rows[1:]:
        row_dict: BridgeRow = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            row_dict[header] = raw_row[index] if index < len(raw_row) else None
        data_rows.append(row_dict)
    return data_rows


def load_bridge_workbook(workbook_file: Path) -> WorkbookRows:
    if not workbook_file.exists():
        raise FileNotFoundError(f"Workbook file not found: {workbook_file}")

    workbook_rows = _read_xlsx_rows(workbook_file)
    required_columns = {
        "Bridge #",
        "County",
        "District",
        "Minimum",
        "Latitude",
        "Longitude",
    }
    available_columns: set[str] = (
        set(workbook_rows[0].keys()) if workbook_rows else set()
    )
    missing = sorted(required_columns.difference(available_columns))
    if missing:
        raise ValueError(f"Workbook is missing required columns: {missing}")
    return workbook_rows


def _prompt_choice(message: str, valid_values: set[str]) -> str:
    while True:
        response = input(message).strip().upper()
        if response in valid_values:
            return response
        print("Invalid selection. Try again.")


def _prompt_int_range(message: str, minimum: int, maximum: int) -> int:
    while True:
        response = input(message).strip()
        try:
            value = int(response)
        except ValueError:
            print("Enter an integer value.")
            continue
        if minimum <= value <= maximum:
            return value
        print(f"Value must be between {minimum} and {maximum}.")


def _prompt_optional_float(message: str, default: float) -> float:
    while True:
        response = input(message).strip()
        if not response:
            return default
        try:
            return float(response)
        except ValueError:
            print("Enter a numeric value or leave blank.")


def choose_counties_interactively(bridge_rows: WorkbookRows) -> list[str]:
    counties = sorted(
        {
            _normalize_county(row.get("County"))
            for row in bridge_rows
            if _normalize_county(row.get("County"))
        }
    )
    county_to_index = {county: index + 1 for index, county in enumerate(counties)}

    print("\nAvailable counties (select 1-2):")
    for county in counties:
        print(f"  {county_to_index[county]:>3}: {county}")

    while True:
        raw = input(
            "\nEnter county numbers or names (comma-separated, 1-2 values): "
        ).strip()
        tokens = [token.strip() for token in raw.split(",") if token.strip()]
        if not 1 <= len(tokens) <= 2:
            print("Choose exactly 1 or 2 counties.")
            continue

        selected: list[str] = []
        valid = True
        for token in tokens:
            if token.isdigit():
                index = int(token)
                if 1 <= index <= len(counties):
                    county = counties[index - 1]
                else:
                    valid = False
                    break
            else:
                county = token.upper()
                if county not in county_to_index:
                    valid = False
                    break
            if county not in selected:
                selected.append(county)

        if not valid or not selected:
            print("Invalid county selection. Use listed numbers or exact county names.")
            continue
        if len(selected) > 2:
            print("Choose at most 2 counties.")
            continue
        return selected


def filter_county_bridges(
    bridge_rows: WorkbookRows, selected_counties: list[str], source_graph: nx.Graph[str]
) -> tuple[WorkbookRows, list[str]]:
    county_rows = [
        row
        for row in bridge_rows
        if _normalize_county(row.get("County")) in selected_counties
    ]

    selected_ids: list[str] = []
    source_nodes = {str(node) for node in source_graph.nodes()}
    for row in county_rows:
        bridge_id = _normalize_bridge_id(row.get("Bridge #"))
        if bridge_id and bridge_id in source_nodes and bridge_id != "MoDOT":
            selected_ids.append(bridge_id)

    deduped_ids = sorted(set(selected_ids))
    if not deduped_ids:
        raise ValueError("No bridge nodes found in graph for selected counties")
    return county_rows, deduped_ids


def build_county_bridge_network(
    source_graph: nx.Graph[str],
    county_rows: WorkbookRows,
    selected_bridge_ids: list[str],
    team_config: TeamConfig,
) -> nx.DiGraph[str]:
    bridge_lookup: dict[str, BridgeRow] = {}
    for row in county_rows:
        bridge_id = _normalize_bridge_id(row.get("Bridge #"))
        if bridge_id:
            bridge_lookup[bridge_id] = row

    undirected_subgraph = cast(
        "nx.Graph[str]", source_graph.subgraph(selected_bridge_ids).copy()
    )
    network: nx.DiGraph[str] = nx.DiGraph()
    source_to_template: dict[str, str] = {}

    for index, source_bridge_id in enumerate(
        sorted(undirected_subgraph.nodes()), start=1
    ):
        template_bridge_id = f"B{index:04d}"
        source_to_template[source_bridge_id] = template_bridge_id

        source_attrs = undirected_subgraph.nodes[source_bridge_id]
        row = bridge_lookup.get(source_bridge_id, {})

        minimum_rating = _to_float(
            row.get("Minimum"),
            _to_float(source_attrs.get("minimum_rating"), 3.0),
        )
        bfi = _normalize_bfi(minimum_rating)
        start = 0
        due = _derive_due_date(bfi)

        cost = {
            team: round(
                team_config.base_cost[team] * (1 + team_config.alpha * (1 - bfi)),
                2,
            )
            for team in team_config.teams
        }
        new_bfi = {
            team: min(round(bfi + team_config.delta_functionality[team], 2), 1.0)
            for team in team_config.teams
        }

        network.add_node(
            template_bridge_id,
            OriginalID=source_bridge_id,
            County=_normalize_county(row.get("County")),
            District=_normalize_text(row.get("District")),
            latitude=_to_float(
                row.get("Latitude"),
                _to_float(source_attrs.get("latitude"), 0.0),
            ),
            longitude=_to_float(
                row.get("Longitude"),
                _to_float(source_attrs.get("longitude"), 0.0),
            ),
            lanes_on=int(
                round(
                    _to_float(
                        source_attrs.get("lanes_on"),
                        _to_float(row.get("Lanes On"), 2.0),
                    )
                )
            ),
            minimum_rating=minimum_rating,
            Depot=0,
            Start=start,
            Due=due,
            BFI=bfi,
            cost=cost,
            NewBFI=new_bfi,
        )

    for source_u, source_v, edge_attrs in undirected_subgraph.edges(data=True):
        if source_u == source_v:
            continue
        target_u = source_to_template[source_u]
        target_v = source_to_template[source_v]

        distance_m = _to_float(edge_attrs.get("highway_distance"), 0.0)
        time_hours = _distance_m_to_time_hours(distance_m)
        lanes_u = _to_float(undirected_subgraph.nodes[source_u].get("lanes_on"), 2.0)
        lanes_v = _to_float(undirected_subgraph.nodes[source_v].get("lanes_on"), 2.0)
        avg_lanes = max(1, int(round((lanes_u + lanes_v) / 2.0)))

        edge_template_attrs = {
            "highway_distance": distance_m,
            "length": max(distance_m / 1000.0, 0.1),
            "speed": 80,
            "capacity": 400 + 150 * avg_lanes,
            "Time": time_hours,
        }
        _ = network.add_edge(target_u, target_v, **edge_template_attrs)
        _ = network.add_edge(target_v, target_u, **edge_template_attrs)

    return network


def compute_county_centroids(
    county_rows: WorkbookRows, selected_counties: list[str], source_graph: nx.Graph[str]
) -> dict[str, tuple[float, float]]:
    centroids: dict[str, tuple[float, float]] = {}

    for county in selected_counties:
        county_subset = [
            row for row in county_rows if _normalize_county(row.get("County")) == county
        ]
        lat_values = [
            _to_float(row.get("Latitude"), float("nan")) for row in county_subset
        ]
        lon_values = [
            _to_float(row.get("Longitude"), float("nan")) for row in county_subset
        ]
        valid_latitudes = [value for value in lat_values if not math.isnan(value)]
        valid_longitudes = [value for value in lon_values if not math.isnan(value)]
        if valid_latitudes and valid_longitudes:
            lat = sum(valid_latitudes) / len(valid_latitudes)
            lon = sum(valid_longitudes) / len(valid_longitudes)
            centroids[county] = (lat, lon)
            continue

        fallback_coords: list[tuple[float, float]] = []
        for row in county_subset:
            bridge_id = _normalize_bridge_id(row.get("Bridge #"))
            if bridge_id in source_graph.nodes():
                attrs = source_graph.nodes[bridge_id]
                lat = _to_float(attrs.get("latitude"), float("nan"))
                lon = _to_float(attrs.get("longitude"), float("nan"))
                if not math.isnan(lat) and not math.isnan(lon):
                    fallback_coords.append((lat, lon))
        if fallback_coords:
            lat = sum(item[0] for item in fallback_coords) / len(fallback_coords)
            lon = sum(item[1] for item in fallback_coords) / len(fallback_coords)
            centroids[county] = (lat, lon)

    if not centroids:
        raise ValueError(
            "Failed to compute county centroid locations for depot placement"
        )
    return centroids


def choose_depots_interactively(
    selected_counties: list[str], county_centroids: dict[str, tuple[float, float]]
) -> list[DepotSelection]:
    depot_count = _prompt_int_range(
        "\nHow many depots to add? (1-4): ",
        minimum=1,
        maximum=4,
    )

    depots: list[DepotSelection] = []
    for depot_index in range(1, depot_count + 1):
        print(f"\nDepot {depot_index} configuration")

        if len(selected_counties) == 1:
            county = selected_counties[0]
        else:
            print("Available counties for this depot:")
            for index, county_name in enumerate(selected_counties, start=1):
                print(f"  {index}: {county_name}")
            county_choice = _prompt_choice(
                "Choose county number for this depot: ",
                {str(index) for index in range(1, len(selected_counties) + 1)},
            )
            county = selected_counties[int(county_choice) - 1]

        centroid_lat, centroid_lon = county_centroids[county]
        county_towns = COUNTY_TOWN_DEFAULTS.get(county, [])

        if county_towns:
            print(f"Suggested towns for {county}:")
            for index, (town_name, town_lat, town_lon) in enumerate(
                county_towns, start=1
            ):
                print(f"  {index}: {town_name} ({town_lat:.4f}, {town_lon:.4f})")

            town_choice = _prompt_choice(
                "Choose suggested town number (Enter for 1, C for custom): ",
                {"", "C"}.union(
                    {str(index) for index in range(1, len(county_towns) + 1)}
                ),
            )
            if town_choice == "C":
                default_name = f"{county.title()} Custom Depot"
                default_lat, default_lon = centroid_lat, centroid_lon
            else:
                selected_index = 0 if not town_choice else int(town_choice) - 1
                default_name, default_lat, default_lon = county_towns[selected_index]
        else:
            default_name = f"{county.title()} County Seat"
            default_lat, default_lon = centroid_lat, centroid_lon

        print(f"Default: {default_name} near ({default_lat:.4f}, {default_lon:.4f})")
        name_input = input(
            "Enter depot display name (press Enter to keep default): "
        ).strip()
        depot_name = name_input if name_input else default_name

        depot_lat = _prompt_optional_float(
            f"Latitude override (Enter to keep {default_lat:.6f}): ",
            default_lat,
        )
        depot_lon = _prompt_optional_float(
            f"Longitude override (Enter to keep {default_lon:.6f}): ",
            default_lon,
        )

        depots.append(
            DepotSelection(
                county=county,
                display_name=depot_name,
                latitude=depot_lat,
                longitude=depot_lon,
            )
        )

    return depots


def add_depots_to_network(
    network: nx.DiGraph[str], depots: list[DepotSelection]
) -> None:
    bridge_nodes = [
        node for node, attrs in network.nodes(data=True) if attrs.get("Depot") != 1
    ]
    if not bridge_nodes:
        raise ValueError("Cannot add depots to an empty bridge network")

    connection_count = min(3, len(bridge_nodes))

    for index, depot in enumerate(depots, start=1):
        depot_id = f"D{index}"
        network.add_node(
            depot_id,
            Depot=1,
            County=depot.county,
            depot_name=depot.display_name,
            latitude=depot.latitude,
            longitude=depot.longitude,
        )

        nearest_bridges = sorted(
            bridge_nodes,
            key=lambda bridge_id: _haversine_km(
                depot.latitude,
                depot.longitude,
                _to_float(network.nodes[bridge_id].get("latitude"), depot.latitude),
                _to_float(network.nodes[bridge_id].get("longitude"), depot.longitude),
            ),
        )[:connection_count]

        for bridge_id in nearest_bridges:
            bridge_lat = _to_float(
                network.nodes[bridge_id].get("latitude"), depot.latitude
            )
            bridge_lon = _to_float(
                network.nodes[bridge_id].get("longitude"), depot.longitude
            )
            distance_km = _haversine_km(
                depot.latitude,
                depot.longitude,
                bridge_lat,
                bridge_lon,
            )
            time_hours = max(distance_km / 80.0, 0.01)
            edge_attrs = {
                "highway_distance": distance_km * 1000.0,
                "length": max(distance_km, 0.1),
                "speed": 80,
                "capacity": 700,
                "Time": time_hours,
            }
            _ = network.add_edge(depot_id, bridge_id, **edge_attrs)
            _ = network.add_edge(bridge_id, depot_id, **edge_attrs)


def geospatial_layout(network: nx.DiGraph[str]) -> dict[str, tuple[float, float]]:
    latitudes = [
        _to_float(attrs.get("latitude"), float("nan"))
        for _, attrs in network.nodes(data=True)
    ]
    longitudes = [
        _to_float(attrs.get("longitude"), float("nan"))
        for _, attrs in network.nodes(data=True)
    ]

    valid_latitudes = [value for value in latitudes if not math.isnan(value)]
    valid_longitudes = [value for value in longitudes if not math.isnan(value)]
    if not valid_latitudes or not valid_longitudes:
        spring_positions = nx.spring_layout(network, seed=39, weight="length")
        return {
            str(node_id): (float(coords[0]), float(coords[1]))
            for node_id, coords in spring_positions.items()
        }

    min_lat = min(valid_latitudes)
    min_lon = min(valid_longitudes)
    scale_factor = 1000.0

    positions: dict[str, tuple[float, float]] = {}
    for node_id, attrs in network.nodes(data=True):
        lat = _to_float(attrs.get("latitude"), min_lat)
        lon = _to_float(attrs.get("longitude"), min_lon)
        positions[node_id] = (
            (lon - min_lon) * scale_factor,
            (lat - min_lat) * scale_factor,
        )
    return positions


def save_network_pickle(network: nx.DiGraph[str], output_graph: Path) -> None:
    output_graph.parent.mkdir(parents=True, exist_ok=True)
    with output_graph.open("wb") as file_obj:
        pickle.dump(network, file_obj)


def main() -> None:
    args = build_parser().parse_args()
    team_config = TeamConfig()

    source_graph = load_missouri_graph(args.graph_file)
    bridge_rows = load_bridge_workbook(args.workbook_file)

    selected_counties = choose_counties_interactively(bridge_rows)
    county_rows, selected_bridge_ids = filter_county_bridges(
        bridge_rows,
        selected_counties,
        source_graph,
    )

    network = build_county_bridge_network(
        source_graph,
        county_rows,
        selected_bridge_ids,
        team_config,
    )

    county_centroids = compute_county_centroids(
        county_rows,
        selected_counties,
        source_graph,
    )
    depots = choose_depots_interactively(selected_counties, county_centroids)
    add_depots_to_network(network, depots)

    network.graph["selected_counties"] = selected_counties
    network.graph["depot_display_names"] = [depot.display_name for depot in depots]
    network.graph["source_graph_file"] = str(args.graph_file)
    network.graph["source_workbook_file"] = str(args.workbook_file)

    positions = geospatial_layout(network)
    colors = node_colors(network)
    labels = node_labels(network)
    figure = plot_network(network, positions, colors, labels)

    args.output_plot.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output_plot)
    save_network_pickle(network, args.output_graph)

    if args.show:
        plt.show()

    print("\nMissouri bridge network created successfully.")
    print(f"Selected counties: {selected_counties}")
    print(
        f"Bridge nodes: {sum(1 for _, attrs in network.nodes(data=True) if attrs.get('Depot') != 1)}"
    )
    print(
        f"Depot nodes: {sum(1 for _, attrs in network.nodes(data=True) if attrs.get('Depot') == 1)}"
    )
    print(f"Directed edges: {network.number_of_edges()}")
    print(f"Saved graph pickle: {args.output_graph}")
    print(f"Saved visualization: {args.output_plot}")


if __name__ == "__main__":
    main()
