import argparse
import csv
import math
import pathlib
import zipfile
import xml.etree.ElementTree as ET


NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

FULL_DATASET_SHEET = "worksheets/sheet3.xml"
POLICIES_SHEET = "worksheets/sheet6.xml"
STORAGE_UNITS_SHEET = "worksheets/sheet8.xml"
DISK_POOL_SHEET = "worksheets/sheet11.xml"

DEFAULT_LOCAL_FACTOR = 1.15
DEFAULT_DEDUP_LOCAL_FACTOR = 1.35
DEFAULT_CLOUD_FACTOR = 3.5
DEFAULT_CLOUD_FIXED_OVERHEAD = 900


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Export the Full_Dataset sheet from a NetBackup job summary workbook "
            "as CSV with restore estimate columns."
        )
    )
    parser.add_argument("workbook", help="Path to the NetBackup XLSX workbook")
    parser.add_argument(
        "-o",
        "--output",
        help="Output CSV path. Defaults to <workbook>_full_dataset_restore_estimates.csv",
    )
    parser.add_argument(
        "--local-factor",
        type=float,
        default=DEFAULT_LOCAL_FACTOR,
        help="Multiplier for non-deduplicated local restores. Default: 1.15",
    )
    parser.add_argument(
        "--dedup-local-factor",
        type=float,
        default=DEFAULT_DEDUP_LOCAL_FACTOR,
        help="Multiplier for local restores from deduplicated MSDP/OpenStorage pools. Default: 1.35",
    )
    parser.add_argument(
        "--cloud-factor",
        type=float,
        default=DEFAULT_CLOUD_FACTOR,
        help="Multiplier applied to elapsed_time for cloud recall estimates. Default: 3.5",
    )
    parser.add_argument(
        "--cloud-overhead",
        type=float,
        default=DEFAULT_CLOUD_FIXED_OVERHEAD,
        help="Fixed seconds added to cloud recall estimates. Default: 900",
    )
    parser.add_argument(
        "--policy",
        help="Optional policy filter. If set, only matching policy rows are exported.",
    )
    return parser.parse_args()


def load_shared_strings(workbook_zip):
    shared_strings = []
    try:
        root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    except KeyError:
        return shared_strings

    for item in root.findall(NS + "si"):
        shared_strings.append("".join(text.text or "" for text in item.iter(NS + "t")))
    return shared_strings


def cell_value(cell, shared_strings):
    cell_type = cell.attrib.get("t")
    value_node = cell.find(NS + "v")
    inline_string = cell.find(NS + "is")

    if cell_type == "s" and value_node is not None:
        return shared_strings[int(value_node.text)]
    if cell_type == "inlineStr" and inline_string is not None:
        return "".join(text.text or "" for text in inline_string.iter(NS + "t"))
    if value_node is not None:
        return value_node.text or ""
    return ""


def column_index(cell_reference):
    column = []
    for character in cell_reference:
        if character.isalpha():
            column.append(character)
        else:
            break

    index = 0
    for character in column:
        index = (index * 26) + (ord(character.upper()) - 64)
    return index - 1


def iter_sheet_rows(workbook_zip, worksheet_path, shared_strings):
    root = ET.fromstring(workbook_zip.read("xl/" + worksheet_path))
    for row in root.findall(".//" + NS + "row"):
        values = {}
        max_index = -1
        for cell in row.findall(NS + "c"):
            index = column_index(cell.attrib.get("r", "A1"))
            values[index] = cell_value(cell, shared_strings)
            if index > max_index:
                max_index = index

        if max_index < 0:
            yield []
            continue

        yield [values.get(index, "") for index in range(max_index + 1)]


def sheet_as_dicts(workbook_zip, worksheet_path, shared_strings):
    rows = iter_sheet_rows(workbook_zip, worksheet_path, shared_strings)
    headers = next(rows)
    for row in rows:
        padded = row + [""] * max(0, len(headers) - len(row))
        yield dict(zip(headers, padded))


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def normalize_bool(value):
    return str(value or "").strip().lower() in {"yes", "true", "1"}


def build_policy_map(workbook_zip, shared_strings):
    policy_map = {}
    for row in sheet_as_dicts(workbook_zip, POLICIES_SHEET, shared_strings):
        policy_name = row.get("policy", "")
        if not policy_name:
            continue
        policy_map[policy_name] = row
    return policy_map


def build_storage_unit_map(workbook_zip, shared_strings):
    storage_unit_map = {}
    for row in sheet_as_dicts(workbook_zip, STORAGE_UNITS_SHEET, shared_strings):
        label = row.get("Label", "")
        if not label:
            continue
        storage_unit_map[label] = row
    return storage_unit_map


def build_disk_pool_flags(workbook_zip, shared_strings):
    disk_pool_flags = {}
    for row in sheet_as_dicts(workbook_zip, DISK_POOL_SHEET, shared_strings):
        pool_name = row.get("DiskPool", "")
        item = row.get("Configuration_Item", "")
        value = row.get("Value", "")
        if not pool_name:
            continue

        disk_pool_flags.setdefault(pool_name, {"flags": set(), "disk_type": "", "comment": ""})
        if item == "Flag" and value:
            disk_pool_flags[pool_name]["flags"].add(value)
        elif item == "Disk Type":
            disk_pool_flags[pool_name]["disk_type"] = value
        elif item == "Comment":
            disk_pool_flags[pool_name]["comment"] = value
    return disk_pool_flags


def is_deduplicated_storage(storage_unit_row, disk_pool_info):
    unit_type = (storage_unit_row.get("Storage_Unit_Type", "") or "").lower()
    subtype = (storage_unit_row.get("Storage_Unit_Subtype", "") or "").lower()
    disk_pool = storage_unit_row.get("Disk_Pool", "")
    flags = disk_pool_info.get("flags", set()) if disk_pool_info else set()
    disk_type = (disk_pool_info.get("disk_type", "") if disk_pool_info else "").lower()

    return any(
        condition
        for condition in (
            disk_pool,
            "diskpool" in subtype,
            "opendisk" in subtype,
            "PureDisk" in flags,
            disk_type == "puredisk",
            "OpenStorage" in flags,
            "OptimizedImage" in flags,
            unit_type == "disk" and normalize_bool(storage_unit_row.get("Use_WORM", "")),
        )
    )


def estimate_local_restore(elapsed_time, total_kb, kb_sec, dedup_rate, is_dedup):
    if elapsed_time <= 0:
        return ""

    base_seconds = float(elapsed_time)
    if kb_sec > 0 and total_kb > 0:
        base_seconds = max(base_seconds, total_kb / float(kb_sec))

    multiplier = DEFAULT_DEDUP_LOCAL_FACTOR if is_dedup else DEFAULT_LOCAL_FACTOR
    if dedup_rate >= 0:
        rehydration_penalty = min(max(dedup_rate / 100.0, 0.0), 0.99) * 0.25
        multiplier += rehydration_penalty

    return int(math.ceil(base_seconds * multiplier))


def estimate_cloud_restore(elapsed_time, total_kb, kb_sec):
    if elapsed_time <= 0:
        return ""

    base_seconds = float(elapsed_time)
    if kb_sec > 0 and total_kb > 0:
        base_seconds = max(base_seconds, total_kb / float(kb_sec))

    return int(math.ceil(DEFAULT_CLOUD_FIXED_OVERHEAD + (base_seconds * DEFAULT_CLOUD_FACTOR)))


def format_minutes(seconds_value):
    if seconds_value == "":
        return ""
    return round(float(seconds_value) / 60.0, 2)


def policy_has_cloud_copy(policy_row):
    if not policy_row:
        return False

    lifecycle_enabled = normalize_bool(policy_row.get("Residence_is_Storage_Lifecycle_", ""))
    residence = (policy_row.get("Residence", "") or "").strip().lower()
    return lifecycle_enabled or any(token in residence for token in ("cloud", "archive", "flex", "ire"))


def main():
    args = parse_args()
    workbook_path = pathlib.Path(args.workbook)
    output_path = pathlib.Path(args.output) if args.output else workbook_path.with_name(
        workbook_path.stem + "_full_dataset_restore_estimates.csv"
    )

    global DEFAULT_LOCAL_FACTOR
    global DEFAULT_DEDUP_LOCAL_FACTOR
    global DEFAULT_CLOUD_FACTOR
    global DEFAULT_CLOUD_FIXED_OVERHEAD

    DEFAULT_LOCAL_FACTOR = args.local_factor
    DEFAULT_DEDUP_LOCAL_FACTOR = args.dedup_local_factor
    DEFAULT_CLOUD_FACTOR = args.cloud_factor
    DEFAULT_CLOUD_FIXED_OVERHEAD = args.cloud_overhead

    with zipfile.ZipFile(workbook_path) as workbook_zip:
        shared_strings = load_shared_strings(workbook_zip)
        policy_map = build_policy_map(workbook_zip, shared_strings)
        storage_unit_map = build_storage_unit_map(workbook_zip, shared_strings)
        disk_pool_flags = build_disk_pool_flags(workbook_zip, shared_strings)

        dataset_rows = sheet_as_dicts(workbook_zip, FULL_DATASET_SHEET, shared_strings)
        first_row = next(dataset_rows)
        base_headers = list(first_row.keys())
        dataset_rows = [first_row] + list(dataset_rows)

    extra_headers = [
        "policy_residence",
        "policy_residence_is_slp",
        "storage_unit_disk_pool",
        "storage_unit_is_deduplicated",
        "restore_estimate_basis",
        "local_restore_seconds",
        "local_restore_minutes",
        "cloud_restore_seconds",
        "cloud_restore_minutes",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=base_headers + extra_headers)
        writer.writeheader()

        exported_rows = 0
        for row in dataset_rows:
            if args.policy and row.get("policy") != args.policy:
                continue

            policy_name = row.get("policy", "")
            storage_unit_name = row.get("storage_unit", "")
            policy_row = policy_map.get(policy_name, {})
            storage_unit_row = storage_unit_map.get(storage_unit_name, {})
            disk_pool_name = storage_unit_row.get("Disk_Pool", "")
            disk_pool_info = disk_pool_flags.get(disk_pool_name, {})

            elapsed_time = safe_int(row.get("elapsed_time"))
            total_kb = safe_int(row.get("total_KB"))
            kb_sec = safe_int(row.get("KB_sec"))
            dedup_rate = safe_float(row.get("dedup_rate"), default=-1.0)

            is_dedup = is_deduplicated_storage(storage_unit_row, disk_pool_info)
            local_restore_seconds = estimate_local_restore(
                elapsed_time=elapsed_time,
                total_kb=total_kb,
                kb_sec=kb_sec,
                dedup_rate=dedup_rate,
                is_dedup=is_dedup,
            )
            cloud_restore_seconds = ""
            if policy_has_cloud_copy(policy_row):
                cloud_restore_seconds = estimate_cloud_restore(
                    elapsed_time=elapsed_time,
                    total_kb=total_kb,
                    kb_sec=kb_sec,
                )

            enriched_row = dict(row)
            enriched_row.update(
                {
                    "policy_residence": policy_row.get("Residence", ""),
                    "policy_residence_is_slp": "yes"
                    if normalize_bool(policy_row.get("Residence_is_Storage_Lifecycle_", ""))
                    else "no",
                    "storage_unit_disk_pool": disk_pool_name,
                    "storage_unit_is_deduplicated": "yes" if is_dedup else "no",
                    "restore_estimate_basis": (
                        "elapsed_time_and_kb_sec_with_dedup_rehydration"
                        if is_dedup
                        else "elapsed_time_and_kb_sec"
                    ),
                    "local_restore_seconds": local_restore_seconds,
                    "local_restore_minutes": format_minutes(local_restore_seconds),
                    "cloud_restore_seconds": cloud_restore_seconds,
                    "cloud_restore_minutes": format_minutes(cloud_restore_seconds),
                }
            )
            writer.writerow(enriched_row)
            exported_rows += 1

    print(f"Wrote {exported_rows} rows to {output_path}")


if __name__ == "__main__":
    main()