import polars as pl
from collections import defaultdict

def accurate_deployment(production_plan, demand_data, max_days=45):
    """TRACK SENT STOCK VERSION - Avoids over-sending and covers all risks"""
    
    deployments = []
    
    # Track what we've already sent to each store
    # {(store_id, item_id): total_units_sent}
    sent_to_store = defaultdict(float)
    
    # Track shipments in transit by arrival day
    # {(store_id, item_id, arrival_day): units_coming}
    in_transit = defaultdict(float)
    
    for day in range(1, max_days + 1):
        daily_prod = production_plan.filter(pl.col("day") == day)
        
        for prod in daily_prod.iter_rows(named=True):
            plant = prod["plant_id"]
            item = prod["item_id"]
            qty = prod["production_quantity"] + prod["starting_inventory_plant"]
            
            if qty <= 0:
                continue
            
            
            # Find stores this plant serves
            stores = demand_data.filter(
                (pl.col("plant_id") == plant) & 
                (pl.col("item_id") == item) &
                (pl.col("day") == day)
            )
            
            if stores.height == 0:
                continue
            

            remaining = qty
            
            # PASS 1: CRITICAL RISK - Stores that will be OUT OF STOCK soon
            critical_stores = []
            for store in stores.iter_rows(named=True):
                store_id = store["store_id"]
                
                # Calculate what's already coming to this store
                key = (store_id, item)
                already_sent = sent_to_store[key]
                
                # Calculate days until stockout considering what we've sent
                current_stock = store["projection"] + already_sent
                days_until_oos = current_stock / store["avg_daily_demand"] if store["avg_daily_demand"] > 0 else 999
                
                # Critical if will stockout within transit time + 2 days
                risk_period = store["transit_time_days"] + 2
                
                if days_until_oos < risk_period:
                    need = (risk_period * store["avg_daily_demand"]) - current_stock
                    critical_stores.append({
                        "store": store,
                        "need": max(0, need),
                        "days_until_oos": days_until_oos
                    })
            
 
            critical_stores.sort(key=lambda x: x["days_until_oos"])
            
            for critical in critical_stores:
                if remaining <= 0:
                    break
                    
                store = critical["store"]
                need = critical["need"]
                send = min(need, remaining)
                
                deployments.append({
                    "day": day, "plant_id": plant, "item_id": item, 
                    "store_id": store["store_id"], "quantity": send,
                    "arrival_day": day + store["transit_time_days"], "priority": "critical_risk"
                })
                
                # Update tracking
                key = (store["store_id"], item)
                sent_to_store[key] += send
                remaining -= send

            
            # PASS 2: Fill safety stock gaps (only if not already addressed)
            if remaining > 0:
                for store in stores.iter_rows(named=True):
                    if remaining <= 0:
                        break
                    
                    store_id = store["store_id"]
                    key = (store_id, item)
                    already_sent = sent_to_store[key]
                    
                    # Current stock + what we've sent
                    effective_stock = store["projection"] + already_sent
                    
                    # Only fill if still below safety stock after what we've sent
                    if effective_stock < store["safety_stock_static"]:
                        need = store["safety_stock_static"] - effective_stock
                        send = min(need, remaining)
                        
                        deployments.append({
                            "day": day, "plant_id": plant, "item_id": item, 
                            "store_id": store["store_id"], "quantity": send,
                            "arrival_day": day + store["transit_time_days"], "priority": "safety_stock"
                        })
                        
                        sent_to_store[key] += send
                        remaining -= send
            

            if remaining > 0:
                high_risk_stores = []
                for store in stores.iter_rows(named=True):
                    store_id = store["store_id"]
                    key = (store_id, item)
                    already_sent = sent_to_store[key]
                    effective_stock = store["projection"] + already_sent
                    
                    # Calculate risk level (lower buffer = higher risk)
                    buffer_ratio = effective_stock / store["safety_stock_static"] if store["safety_stock_static"] > 0 else 1
                    
                    if buffer_ratio < 2.0:  # Less than 2x safety stock is considered risky
                        need = (2.0 * store["safety_stock_static"]) - effective_stock
                        high_risk_stores.append({
                            "store": store,
                            "need": max(0, need),
                            "buffer_ratio": buffer_ratio
                        })
                
                # Send to stores with lowest buffers first
                high_risk_stores.sort(key=lambda x: x["buffer_ratio"])
                
                for risk_store in high_risk_stores:
                    if remaining <= 0:
                        break
                    
                    store = risk_store["store"]
                    need = risk_store["need"]
                    send = min(need, remaining)
                    
                    deployments.append({
                        "day": day, "plant_id": plant, "item_id": item, 
                        "store_id": store["store_id"], "quantity": send,
                        "arrival_day": day + store["transit_time_days"], "priority": "buffer_stock"
                    })
                    
                    key = (store["store_id"], item)
                    sent_to_store[key] += send
                    remaining -= send

            
            # PASS 4: Distribute whatever's left (FIXED - no leftovers)
            if remaining > 0:
                total_demand = stores["avg_daily_demand"].sum()
                
                distributed = 0
                store_allocation = []
                
                for i, store in enumerate(stores.iter_rows(named=True)):
                    if total_demand > 0:
                        share = store["avg_daily_demand"] / total_demand
                        allocated = remaining * share
                    else:
                        allocated = remaining / len(stores)
                    
                    # Last store gets whatever's left to avoid rounding errors
                    if i == len(stores) - 1:
                        allocated = remaining - distributed
                    else:
                        distributed += allocated
                    
                    store_allocation.append({
                        "store": store,
                        "allocated": allocated
                    })
                
                for allocation in store_allocation:
                    store = allocation["store"]
                    send = allocation["allocated"]
                    
                    if send > 0:
                        deployments.append({
                            "day": day, "plant_id": plant, "item_id": item, 
                            "store_id": store["store_id"], "quantity": send,
                            "arrival_day": day + store["transit_time_days"], "priority": "leftover"
                        })
                        
                        key = (store["store_id"], item)
                        sent_to_store[key] += send

                
                remaining = 0
            

    
    # FINAL REPORT
    total_production = production_plan.filter(pl.col("day") <= max_days)["production_quantity"].sum()
    deployment_df = pl.DataFrame(deployments)
    
    if deployment_df.height > 0:
        total_deployed = deployment_df["quantity"].sum()
        
    else:
        total_deployed = 0
    
    
    return deployment_df