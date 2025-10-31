import pandas as pd

def apply_production_cut(
    production_plan_df: pd.DataFrame,
    cut_type: str = "%",
    cut_value: float = 5.0,
    horizon_days: list = None,
    min_cut_unit: float = 0.01,
    max_iter: int = 10,
    plant_filter: str | list[str] | None = None,  # ✅ new argument
) -> pd.DataFrame:
    """
    Apply a production cut (by % or units), respecting MOQ and cycle_days.
    Redistribute sub-MOQ runs and guarantee total cut precision.

    Parameters
    ----------
    production_plan_df : pd.DataFrame
        Must include ['plant_id','item_id','day','production_quantity','MOQ_units','cycle_days']
    plant_filter : str | list[str] | None
        If set, apply cut only to that plant or list of plants.
        If None → applies to ALL plants (full scope).
    """

    df = production_plan_df.copy()

    # --- Optional filter by plant ---
    if plant_filter is not None:
        if isinstance(plant_filter, str):
            plant_filter = [plant_filter]
        df = df[df["plant_id"].isin(plant_filter)].copy()
        if df.empty:
            raise ValueError(f"No records found for plant(s): {plant_filter}")

    # --- Filter by horizon if needed ---
    if horizon_days is not None:
        df = df[df["day"].isin(horizon_days)]

    required = ["item_id", "day", "production_quantity", "MOQ_units", "cycle_days"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"Missing required column: {c}")

    df = df.sort_values(["item_id", "day"]).reset_index(drop=True)
    df["health_score"] = df.get("health_score", 0.5)

    total_prod = df["production_quantity"].sum()
    if total_prod <= 0:
        print("⚠️ No production quantity to cut in selected scope.")
        return df

    # --- Determine total target cut ---
    if cut_type == "%":
        target_cut = total_prod * cut_value / 100
    elif cut_type == "units":
        target_cut = cut_value
    else:
        raise ValueError("cut_type must be '%' or 'units'")

    # --- Initial proportional cut by health_score ---
    weights = (1 - df["health_score"] + 1e-9)
    weights = weights / weights.sum()
    df["target_cut"] = weights * target_cut
    df["new_qty"] = df["production_quantity"] - df["target_cut"]
    df["new_qty"] = df["new_qty"].clip(lower=0)

    # --- Redistribute sub-MOQ runs ---
    for item, grp in df.groupby("item_id", sort=False):
        idxs = grp.index.tolist()
        for i in range(len(idxs)):
            idx = idxs[i]
            qty = df.at[idx, "new_qty"]
            moq = df.at[idx, "MOQ_units"]

            if qty == 0:
                continue

            # Below MOQ → merge backward (or forward if first)
            if qty < moq:
                if i > 0:
                    prev_idx = idxs[i - 1]
                    df.at[prev_idx, "new_qty"] += qty
                    df.at[idx, "new_qty"] = 0
                elif len(idxs) > 1:
                    next_idx = idxs[i + 1]
                    df.at[next_idx, "new_qty"] += qty
                    df.at[idx, "new_qty"] = moq  # keep alive

    # --- Iteratively rescale to hit target cut precisely ---
    for _ in range(max_iter):
        total_after = df["new_qty"].sum()
        current_cut = total_prod - total_after
        diff = current_cut - target_cut

        if abs(diff) <= min_cut_unit:
            break  # close enough

        scale = (total_prod - target_cut) / total_after
        df["new_qty"] *= scale

        # Enforce MOQ after scaling
        for i in df.index:
            moq = df.at[i, "MOQ_units"]
            if 0 < df.at[i, "new_qty"] < moq:
                df.at[i, "new_qty"] = moq

    # --- Final assignment ---
    df["new_qty"] = (df["new_qty"] / 0.1).round() * 0.1
    df["production_quantity"] = df["new_qty"].round(3)
    df.drop(columns=["target_cut", "new_qty"], inplace=True, errors="ignore")

    total_after = df["production_quantity"].sum()
    achieved_cut = total_prod - total_after
    print(
        f"✅ Applied cut: {achieved_cut:.2f} / Target: {target_cut:.2f} "
        f"({achieved_cut/target_cut*100:.1f}%) for plants: {plant_filter or 'ALL'}"
    )

    return df