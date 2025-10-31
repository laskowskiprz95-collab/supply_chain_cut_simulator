import polars as pl

def build_rating(rate_df: pl.DataFrame) -> pl.DataFrame:
    # --- Step 1: Protect against zero SS ---
    rate_df = rate_df.with_columns([
        pl.when(pl.col("safety_stock_static") <= 0)
          .then(0.001)
          .otherwise(pl.col("safety_stock_static"))
          .alias("safety_stock_safe")
    ])

    # --- Step 2: Calculate daily metrics ---
    df_metrics = rate_df.with_columns([
        (pl.col("inv_projection") / pl.col("safety_stock_safe"))
            .alias("coverage_ratio"),
        (pl.col("SS_risk_peak").abs() / pl.col("safety_stock_safe"))
            .alias("relative_risk"),
        (pl.col("OOS_risk_projection") < 0)
            .cast(pl.Float64)
            .alias("stockout_flag"),
        # NEW A: production vs forecast ratio (guard against /0)
        (pl.col("production_quantity") / (pl.col("forecast_sales") + 1e-6))
            .alias("prod_forecast_ratio"),
        # NEW B: economic weight proxy
        (pl.col("sell_price") * pl.col("forecast_sales"))
            .alias("revenue_weight")
    ])

    # --- Step 3: Aggregate per plant + item ---
    rating_df = (
        df_metrics
        .group_by(["plant_id", "item_id"])
        .agg([
            pl.col("coverage_ratio").mean().fill_nan(0).alias("avg_coverage_ratio"),
            pl.col("relative_risk").mean().fill_nan(0).alias("avg_relative_risk"),
            pl.col("stockout_flag").mean().fill_nan(0).alias("stockout_frequency"),
            # NEW A aggregate
            pl.col("prod_forecast_ratio").mean().fill_nan(0).alias("avg_prod_forecast_ratio"),
            # NEW B aggregate
            pl.col("revenue_weight").mean().fill_nan(0).alias("avg_revenue_weight"),
            # NEW C: risk volatility
            pl.col("OOS_risk_projection").std().fill_nan(0).alias("risk_volatility"),
        ])
    )

    # --- Step 4: Handle infinities ---
    rating_df = rating_df.with_columns([
        pl.when(pl.col("avg_coverage_ratio").is_infinite()).then(0).otherwise(pl.col("avg_coverage_ratio")).alias("avg_coverage_ratio"),
        
        pl.when(pl.col("avg_relative_risk").is_infinite()).then(0).otherwise(pl.col("avg_relative_risk")).alias("avg_relative_risk")
    ])

    # --- Step 5: Normalization helper ---
    def normalize(expr):
        min_val = expr.min()
        max_val = expr.max()
        return pl.when(max_val - min_val == 0).then(0).otherwise((expr - min_val) / (max_val - min_val))

    # --- Step 6: Normalize all metrics ---
    rating_df = rating_df.with_columns([
        normalize(pl.col("avg_coverage_ratio")).alias("coverage_norm"),
        normalize(pl.col("avg_relative_risk")).alias("risk_norm"),
        normalize(pl.col("stockout_frequency")).alias("stockout_norm"),
        normalize(pl.col("avg_prod_forecast_ratio")).alias("prod_forecast_norm"),
        normalize(pl.col("avg_revenue_weight")).alias("revenue_norm"),
        normalize(pl.col("risk_volatility")).alias("volatility_norm"),
    ])

    # --- Step 7: Composite health_score ---
    rating_df = rating_df.with_columns([
        (
            0.35 * pl.col("coverage_norm") +           # supply buffer
            0.25 * pl.col("risk_norm") +               # relative risk
            0.20 * pl.col("stockout_norm") +           # stockout frequency
            0.10 * pl.col("prod_forecast_norm") +      # overproduction = safer
            0.07 * (1 - pl.col("revenue_norm"))+            # protect high revenue items
            0.03 * pl.col("volatility_norm")           # small weight for uncertainty
        ).alias("health_score")
    ])

    return rating_df.select([
        "plant_id", "item_id",
        "avg_coverage_ratio", "avg_relative_risk", "stockout_frequency",
        "avg_prod_forecast_ratio", "avg_revenue_weight", "risk_volatility",
        "health_score"
    ])