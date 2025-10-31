<div align="center">
    
## 🏭 Production Cut Simulator
</div>

Risk-Aware Supply Chain Optimization in 30-Days

A fast, modular simulation that shows how reduction of production effects supply chain, impacting service stability, safety stock and transportation needs. Build to explain complex business implications as data driven insight. 

<div align="center">

## 💡 Why I Built This
</div> 
When taking strategic decisions in supply chain more often than not it's a balancing act in short term we would want to overprotect service levels, but production, transportation, warehousing all have costs so finding a right balance becomes critical at that time, the right information is the most valuable.

This project aims to simulate a 30-day scope contained in a simulated multi-plant, multi-dc network to see how production cut affects:

💠deployment plan
💠safety stock coverage
💠impact to service

all across 150 SKUs

Because the subject of this simulation is considered sensitive data what I aimed to do was to simulate every key master-data element like pallet size, truck size and MOQ as well as general supply chain structure.
My goal was to combine forecasting, production and distribution into one end-to-end pipeline that is able to tell a clear story.

<div align="center">

## 🔍 Project Overview
</div> 
A concise, three-step flow:

💠 Step 1 - Data Preparation
Build on M5 Forecasting data, this step generates a fundamental elements:

    🔸30-day-demand projection (Exponential Smoothing)
    🔸Plant-Store-SKU level demand outlook with safety stock
    🔸Plant-SKU level for combined demand (as requirements for production)
    🔸Starting inventory for both plant's and stores 
    🔸Pallet sizes, Lane transit times, SKU most recent prizes 
💠 Step 2 - Production & Deployment Planning:

    🔸Plan production plan across 3 plants under realistic cycle and MOQ constrains
    🔸Simulate deployment to 5 Stores based on lead-time and "full-truck only" restriction 
💠 Step 3 - Simulation % Risk Projection:

    🔸Combines demand outlook with deployment results to create 30-day service / safety stock projection
    🔸Applies a "production cut" (e.g., -10%) and re-evaluates deployment and projection
    🔸Directs the production cut using an SKU scoring system that evaluates SKUs for ideal:
        🔹stock-out probability
        🔹Inventory and safety build-up / shortage
        🔹Price of the SKU
        🔹Over and Underproduction

▶️ Output: clean "before vs after" comparison showing trade-off of production cost saving.

<div align="center">

## ⚙ Tech & Tools
</div> 

|Category| Tools / Concepts |
|:-------|:-----------------|
|**DataM5**|Forecasting dataset, Polars, NumPy|
|**Forecasting**|Exponential Smoothing|
|**Modeling**|Risk-aware production & transport planning|
|**Simulation**|Custom production cut engine|
|**Visualization**|Matplotlib, Seaborn|
|**Design**|Modular src/ structure, 45-day scalable horizon|

The full simulation (production + transport + risk) runs in seconds on sample data - a lightweight yet realistic sandbox for supply-chain experimentation.

<div align="center">

## 🚀 What Makes It Different
</div> 
Unlike static optimization models, this project connects the entire chain (forecast ➠ production ➠ deployment ➠ service risk) into one rapid-iteration simulation.

It’s designed for speed, scalability, and storytelling:

Most data prep runs in Polars for near-instant aggregation
Cut parameters can be adjusted (% or Units for target cut, full scope (all 3 plants) or specific one) can be adjusted in-notebook
Built with modular functions for reuse in larger supply-chain prototypes

<div align="center">

## 📊 Results Snapshot
</div> 
Example scenario: 150 SKUs, 3 plants, 5 DCs 30-days of planning horizon (extended calc to 45-days to avoid end-of-month artifacts):
10% production cut on low-margin SKUs
Key takeaways:

    🔸Case Fill Rate stayed stable (99.86 % ➠ 99.54 %) that is worth $610 in losses 
    🔸Cut Generated extra 19.5% gap in Safety Stock (-50.83% ➠-70.25%) that is worth ~ $8K
    🔸Production value decreased by $13.2K, with proportional cuts across all plants.
    🔸Deployment efficiency improved as expected with 47 less trucks scheduled between 3 plants in a month

Overall, model proves that in this supply chain structure there is space for a controlled 10% production cut and resulting losses do not outweigh the benefits. More details and visuals are in the notebooks.

<div align="center">
    
## 🧭 If I Were to Take It to Production
</div>
While the current model captures the core dynamic of the supply chain, taking it to production would require integration of a richer, real-world data. Many of these elements were simplified when synthetically created to help with realism of the project, the realistic modeling of these factors would require data that is rarely if ever available in open datasets.
To evolve this proof-of-concept into a deployable tool, I would extend:

    🔸Production capacity and shift plan - to simulate cuts as shift reductions or maintenance windows   
    🔸Transportation capacity - model deployment simulation based on expected truck limits
    🔸Integration of bill of material - our reduction of production also has rippling effect on raw and pack materials these are not explored here but could be useful

Each step would turn the simulation into a more complete digital planning twin, maintaining the same modular architecture and compute efficiency.

<div align="center">

## 🧩 How to Run
</div> 
    Clone the repository:
    
    🔸Run 01_Data_Prep.ipynb → generates base datasets
    🔸Run 02_Production_Transport.ipynb → builds plan and deployment
    🔸Run 03_Projection_Simulation.ipynb → runs the cut and visualizes results

All paths and parameters are easily editable in-notebook.
(No special config file required - self-contained and ready to explore.)

<div align="center">

## 🗂️ Data Availability
This project uses public data from [M5 Forecasting Accuracy Competition](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data)
To reproduce results, download the following files and place them in the `/Input M5/` folder:

- `sales_train_evaluation.csv`
- `sell_prices.csv`
- `calendar.csv`

These files are too large for GitHub storage and are **excluded from the repository** to keep it lightweight.  
All scripts and notebooks will automatically detect them if placed in the correct directory.

</div> 
<div align="center">

## 🤝 Connect
</div> 
This project reflects how I approach real-world supply-chain problems:
combine data discipline, business context, and system-level reasoning.

💬 Let’s connect if you’d like to discuss:
    risk-aware supply planning,
    scenario simulation,
    end-to-end supply chain modeling.