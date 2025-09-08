# Welcome to the Interactive Hippocampal UMAP App!

This code is deployed live on Google Cloud! View it (here)[https://my-umap-service-168673687771.us-central1.run.app/]

This is an app designed to allow users to interactively view differences in structural connectivity profiles involving the hippocampus in the rat brain. What does that mean? I'll break it down:

### Data

The data here comes from Swanson et al (2024), and is the structural connectivity of the whole rat brain, averaged between hemispheres and sex (hemispheric and sex differences in connectivity is negligble). The connections are represented using a matrix, such that connection from the row region i to column region j is represented by the entry $A_{ij}$. Connection values range from 0 (no connection) to 7 (strong connection) and represent density of axons.

### Analysis

We are interested in how the hippocampus is connected to other regions, which can be characterized by afferent (incoming) and efferent (outgoing) connections. We defined the hippocampus as being composed of seven subregions: Dentate gyrus, ventral and dorsal CA1, CA2, CA3, and ventral and dorsal subiculum. 

Next, the data was filtered to only include connections between regions that include at least one of these subregions, which produced an efferent hippocampal connectome and afferent hippocampal connectome.

UMAP was applied to both of these connectomes in order to visualize how connections with various brain regions differ in terms of patterns of connection with the hippocampus. This app allows the users to interactively view these UMAP plots and change the `n_neighbors` and `min_dist` parameters, allowing users to specify how much local vs global structure they wish to capture. 

#### Copyright

Copyright 2025 Chris Weinberger

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.



