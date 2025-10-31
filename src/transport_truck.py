import pandas as pd
def simulate_truck_allocation_pandas(daily_df: pd.DataFrame, truck_capacity: float = 34.0) -> pd.DataFrame:
    # Normalize expected column names (case/space tolerant)
    df = daily_df.rename(columns={c: c.strip().lower().replace(" ", "_") for c in daily_df.columns}).copy()

    # required cols
    required = {"day","plant_id","store_id","item_id","priority","pallet_size","store_pallet_total"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # priority ordering map (text -> rank)
    prio_order = {
        "critical_risk": 1,
        "safety_stock": 2,
        "buffer_stock": 3,
        "leftover": 4
    }
    df["priority_rank"] = df["priority"].map(prio_order).fillna(99).astype(int)

    results = []

    # iterate per lane
    for (plant, store), lane_df in df.groupby(["plant_id","store_id"]):
        lane_df = lane_df.copy()
        days = sorted(lane_df["day"].unique())

        # carryover list of dicts: item_id, priority, priority_rank, pallet_size, pallets
        carryover = []

        for day in days:
            todays = lane_df[lane_df["day"] == day]

            # entries start with carryover
            entries = []
            for c in carryover:
                entries.append(dict(c))

            # add today's aggregated rows grouped by item/priority/pallet_size
            agg = (todays.groupby(["item_id","priority","priority_rank","pallet_size"], as_index=False)
                       ["store_pallet_total"].sum())
            for _, r in agg.iterrows():
                entries.append({
                    "item_id": r["item_id"],
                    "priority": r["priority"],
                    "priority_rank": int(r["priority_rank"]),
                    "pallet_size": float(r["pallet_size"]),
                    "pallets": float(r["store_pallet_total"])
                })

            # combine entries with same (item, priority, pallet_size)
            combined = {}
            for e in entries:
                key = (e["item_id"], e["priority"], float(e["pallet_size"]))
                if key not in combined:
                    combined[key] = {
                        "item_id": e["item_id"],
                        "priority": e["priority"],
                        "priority_rank": int(e["priority_rank"]),
                        "pallet_size": float(e["pallet_size"]),
                        "pallets": 0.0
                    }
                combined[key]["pallets"] += float(e.get("pallets", 0.0))

            # deterministic ordering: priority_rank asc, then item_id
            entry_list = sorted(combined.values(), key=lambda x: (x["priority_rank"], str(x["item_id"])))

            total_pallets = sum(e["pallets"] for e in entry_list)
            num_full_trucks = int(total_pallets // truck_capacity)
            pallets_to_send = num_full_trucks * truck_capacity
            remaining_to_send = pallets_to_send
            trucks_sent = num_full_trucks

            per_entry = []
            for e in entry_list:
                available = e["pallets"]
                send = 0.0
                if remaining_to_send > 0:
                    send = min(available, remaining_to_send)
                leftover = available - send
                per_entry.append({
                    "day": day,
                    "plant_id": plant,
                    "store_id": store,
                    "item_id": e["item_id"],
                    "priority": e["priority"],
                    "pallet_size": e["pallet_size"],
                    "pallets_available": available,
                    "pallets_sent": send,
                    "pallets_carryover": leftover,
                    "qty_available": available * e["pallet_size"],
                    "qty_sent": send * e["pallet_size"],
                    "qty_carryover": leftover * e["pallet_size"],
                    "trucks_sent": trucks_sent
                })
                remaining_to_send -= send

            # new carryover for next day
            carryover = []
            for row in per_entry:
                if row["pallets_carryover"] > 1e-9:
                    carryover.append({
                        "item_id": row["item_id"],
                        "priority": row["priority"],
                        "priority_rank": prio_order.get(row["priority"], 99),
                        "pallet_size": row["pallet_size"],
                        "pallets": row["pallets_carryover"]
                    })

            results.extend(per_entry)

    out = pd.DataFrame(results)
    if out.empty:
        return out
    out = out.sort_values(["day","plant_id","store_id","priority","item_id"]).reset_index(drop=True)
    return out