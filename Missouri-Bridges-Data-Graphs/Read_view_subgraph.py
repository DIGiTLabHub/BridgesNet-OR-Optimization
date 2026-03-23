#!/usr/bin/env python
# coding: utf-8

# In[1]:


# Re-load necessary libraries and data since execution state was reset
import pandas as pd
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import pickle


# In[2]:


def create_subgraph(G, df, districts=None, counties=None):
    """
    Creates a subgraph based on a set of districts and/or counties.
    If both districts and counties are provided, takes the union of the results.
    Always includes 'MoDOT' in the subgraph.

    Parameters:
    - G: The full graph.
    - df: The dataframe containing bridge information.
    - districts: A set or list of district numbers (optional).
    - counties: A set or list of county names (optional).

    Returns:
    - A subgraph containing the selected nodes and edges.
    """
    if districts is None and counties is None:
        raise ValueError("You must provide either districts or counties.")

    selected_bridges = set()  # Use a set to avoid duplicates

    # Ensure districts is iterable (e.g., set or list)
    if districts:
        districts = set(map(str, districts))  # Convert all district numbers to strings
        district_bridges = df[df['District'].astype(str).isin(districts)]['Bridge #'].tolist()
        selected_bridges.update(district_bridges)

    # Ensure counties is iterable (e.g., set or list)
    if counties:
        # Normalize county names to uppercase for case-insensitive matching
        counties = {c.upper() for c in counties}
        county_bridges = df[df['County'].str.upper().isin(counties)]['Bridge #'].tolist()
        selected_bridges.update(county_bridges)

    # Ensure 'MoDOT' is always included
    selected_bridges.add("MoDOT")

    # Check if any bridges were selected; if not, warn and return only 'MoDOT'
    if len(selected_bridges) == 1:  # Only 'MoDOT' is included
        print("⚠️ No bridges found for the given districts or counties. Only 'MoDOT' will be included.")

    # Create the subgraph with selected bridges
    subgraph = G.subgraph(selected_bridges).copy()

    return subgraph


# In[3]:


# ========== FUNCTION TO VISUALIZE THE SUBGRAPH ==========
def visualize_subgraph(G_sub):
    """
    Visualizes the subgraph with nodes positioned using scaled real-world distances.
    """
    plt.figure(figsize=(10, 8))

    # Extract latitude and longitude from graph nodes
    latitudes = np.array([G_sub.nodes[node]['latitude'] for node in G_sub.nodes])
    longitudes = np.array([G_sub.nodes[node]['longitude'] for node in G_sub.nodes])

    # Scale coordinates for better visualization
    scale_factor = 1000  # Adjust this value to fine-tune layout scaling
    scaled_positions = {node: ((lon - longitudes.min()) * scale_factor, 
                               (lat - latitudes.min()) * scale_factor) for node, (lat, lon) in zip(G_sub.nodes, zip(latitudes, longitudes))}

    # Draw the graph
    nx.draw(G_sub, pos=scaled_positions, with_labels=True, node_size=300, node_color="red", edge_color="gray", font_size=8)

    # Highlight MoDOT in blue
    nx.draw_networkx_nodes(G_sub, pos=scaled_positions, nodelist=["MoDOT"], node_color="blue", node_size=400)

    plt.title("Subgraph Visualization with Scaled Real-World Distances")

    plt.savefig("subgraph-plot.pdf", format="pdf", bbox_inches="tight")
    # print(f"✅ Graph saved to {output_file}")

    plt.show()


# In[4]:


# ========== SAMPLE USAGE for Subgraph Creation / Viz ==========
# Load the saved graph for the complete set of Missouri Poor Bridges with Physical Distances 
graph_file = "./missouri_bridge_graph.pkl"
with open(graph_file, "rb") as f:
    G_loaded = pickle.load(f)

print("✅ Graph loaded successfully!")

# Load the bridge dataset
file_path = "./MOpoorbridges.xlsx"
df = pd.read_excel(file_path)
# print(df.head())

print("✅ Bridge data loaded successfully!")


# In[5]:


# Specify the district or county to filter
# could be mulitple districts or counties (cap or small letters for counties); 
# the code will take a union of the mapped bridges given the district or the counties
# selected_district = {"1"}  # Example district number 
# selected_county = {"Clinton"}  # Example county name

# use the following different combinations
# selected_districts = {"1"}
# selected_counties = None
# selected_counties = {"Clinton", "DAVIESS", "ATCHISON"}


selected_districts = None
selected_counties = {"Clinton"}

# Generate and visualize the subgraph using a district
# subgraph_district = create_subgraph(G_loaded, df, districts=selected_district)
# visualize_subgraph(subgraph_district)
# Generate and visualize the subgraph using a county
# subgraph_county = create_subgraph(G_loaded, df, counties=selected_county)
# visualize_subgraph(subgraph_county)


# Generate a subgraph using both district or county
subgraph = create_subgraph(G_loaded, df, districts=selected_districts, counties=selected_counties)
visualize_subgraph(subgraph)

# Print edges and their weights (physical distances)
for u, v, attr in subgraph.edges(data=True):
    print(f"Edge: {u} <-> {v}, Distance: {attr['highway_distance']} meters")


# In[6]:


# Save the existing subgraph to a file
subgraph_file = "./missouri_bridge_subgraph_saved.pkl"
with open(subgraph_file, "wb") as f:
    pickle.dump(subgraph, f)
print(f"✅ Subgraph saved to {subgraph_file}")


# In[ ]:




