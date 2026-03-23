#!/usr/bin/env python
# coding: utf-8

# In[4]:


# Re-load necessary libraries and data since execution state was reset
import pandas as pd
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import pickle


# In[7]:


# ========== 6. LOAD THE GRAPH ==========
graph_file = "./missouri_bridge_graph.pkl"
with open(graph_file, "rb") as f:
    G_loaded = pickle.load(f)

print("✅ Graph loaded successfully!")

# ========== 7. PRINT BASIC GRAPH INFORMATION ==========
num_nodes = G_loaded.number_of_nodes()
num_edges = G_loaded.number_of_edges()

print(f"📌 Total Nodes: {num_nodes}")
print(f"📌 Total Edges: {num_edges}")


# In[11]:


# ========== VISUALIZE GRAPH WITHOUT BASEMAP (USING SCALED DISTANCES) ==========
def visualize_graph(G, output_file="MO-poor-bridges-graph.pdf"):
    """
    Visualizes the graph with nodes positioned using scaled real-world distances
    and saves it to a PDF file.

    Parameters:
    - G: The graph to visualize.
    - output_file: The filename for saving the graph as a PDF.
    """
    plt.figure(figsize=(10, 8))

    # Extract latitude and longitude from graph nodes
    latitudes = np.array([G.nodes[node]['latitude'] for node in G.nodes])
    longitudes = np.array([G.nodes[node]['longitude'] for node in G.nodes])

    # Scale coordinates for better visualization
    scale_factor = 1000  # Adjust this value to fine-tune layout scaling
    scaled_positions = {node: ((lon - longitudes.min()) * scale_factor, 
                               (lat - latitudes.min()) * scale_factor) for node, (lat, lon) in zip(G.nodes, zip(latitudes, longitudes))}

    # Draw the graph
    nx.draw(G, pos=scaled_positions, with_labels=True, node_size=300, node_color="red", edge_color="gray", font_size=8)

    # Highlight MoDOT in blue
    nx.draw_networkx_nodes(G, pos=scaled_positions, nodelist=["MoDOT"], node_color="blue", node_size=400)

    # Add title
    plt.title("Graph Visualization with Scaled Real-World Distances")

    # Save to PDF
    plt.savefig(output_file, format="pdf", bbox_inches="tight")
    print(f"✅ Graph saved to {output_file}")

    # Show the plot
    plt.show()

# Call visualization function
visualize_graph(G_loaded)


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




