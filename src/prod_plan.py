import math
import pandas as pd

def build_smarter_production_plan(group):

    group = group.sort_values('day')
    
    production_stock = [0.0] * len(group)
    production_quantity = [0.0] * len(group)
    last_production_day = 0
    buildup = 1.15

    starting_inventory = group[group['day']==1]['starting_inventory_plant'].iloc[0] if not group[group['day']==1].empty else 0
    production_stock[0] = starting_inventory
    
    for i in range(len(group)):
        current_day = group['day'].iloc[i]
        requirement = group['total_daily_requirement'].iloc[i]
        moq = group['MOQ_units'].iloc[i]
        cycle_days = group['cycle_days'].iloc[i]
        
        # Carry over previous stock
        if i > 0:
            production_stock[i] = production_stock[i-1]
        
        # Subtract today's demand
        production_stock[i] -= requirement
        
        # Check if we need to produce
        days_since_last_production = current_day - last_production_day
        can_produce = (last_production_day == 0 or days_since_last_production >= cycle_days)
        
        if production_stock[i] < 0 and can_produce:
            # 🚀 IMPROVEMENT 1: Calculate total deficit over next cycle days
            total_deficit = abs(production_stock[i])  # Start with current deficit
            
            # Look ahead through the cycle period to find additional deficits
            lookahead_end = min(i + cycle_days, len(group))
            
            temp_stock = 0  # We'll simulate forward from current position
            for j in range(i + 1, lookahead_end):
                future_requirement = group['total_daily_requirement'].iloc[j]
                temp_stock -= future_requirement
                if temp_stock < 0:
                    total_deficit += abs(temp_stock)
                    temp_stock = 0  # Reset after covering deficit
            
            # 🚀 IMPROVEMENT 2: Calculate needed MOQ multiples
            if moq > 0:
                moq_multiples = math.ceil(total_deficit / moq)
                production_qty = moq_multiples * moq * buildup
            else:
                production_qty = total_deficit * buildup
            
            # 🚀 IMPROVEMENT 3: Only produce if it makes sense
            if production_qty > 0:
                production_quantity[i] = production_qty
                last_production_day = current_day
                
                # Add production to current and future days
                for j in range(i, len(group)):
                    production_stock[j] += production_qty
    
    # Add results back to group
    group = group.copy()
    group['production_stock'] = production_stock
    group['production_quantity'] = production_quantity
    group['last_production_day'] = last_production_day
    group['plant_starting_inventory_used'] = starting_inventory
    
    return group