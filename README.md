<h1>Guyana Flood Mapping</h1>
<hr>
<h3>Clark University - Advance Remote Sensing - Spring 2024</h3>
<h3>Project by Clio Bate, Claudia Buszta, Hanxi Li, André de Oliveira, Ruthanne Ward</h3>

![Flooding in Rupununi Wetland](assets/07-14.png "Flooding in Rupununi Wetland, July 14 2017")
Flooding in Rupununi Wetland, July 14 2017
<hr>

## Environment Setup Instructions for ASF flood mapping notebooks

<p>These instructions guide you through creating and activating environments necessary for running the notebooks in the ASF_Adaptive_Flood_Mapping directory of this repository. All commands should be executed in the terminal. The notebooks were run in Microsoft Planetary Computer but could be run locally.</p>

<h2>Creating Environments</h2>

<p>Create environments based on the specifications provided in the YAML files located in <code>/home/jovyan/GuyanaFloodMapping/configs/</code>. The first line of each step is for the Big_Hand_notebook_adapted notebook for creating a Height Above Nearest Drainage (HAND) geotif. The second line of each step is for the ASF_Flood_mapping notebook, which uses adaptive thresholding to create surface water maps. Execute the following commands in your terminal:</p>

<p>For the <strong>Big_Hand_notebook_adapted</strong> environment:</p>
<pre><code>conda env create -f /home/jovyan/GuyanaFloodMapping/configs/locked_hydrosar_env.yml</code></pre>

<p>For the <strong>ASF_Flood_mapping</strong> environment:</p>
<pre><code>conda env create -f /home/jovyan/GuyanaFloodMapping/configs/SAR_flooding_env.yml</code></pre>

<h2>Steps to Follow After Creating the Environment</h2>

<h3>Step 1: Activate the Environment</h3>

<p>Activate the environment using one of the following commands based on the specific notebook you intend to run:</p>

<p>For <strong>Big_Hand_notebook_adapted</strong>:</p>
<pre><code>conda activate hydrosar</code></pre>

<p>For <strong>ASF_Flood_mapping</strong>:</p>
<pre><code>conda activate asf-jupyter-notebook</code></pre>
<p>Alternatively, you can specify the path directly:</p>
<pre><code>conda activate /home/jovyan/.local/envs/asf-jupyter-notebook</code></pre>

<h3>Step 2: Install IPython Kernel</h3>

<p>With the environment activated, install <code>ipykernel</code> to enable using this environment as a Jupyter kernel. Run the following command for both environments:</p>
<pre><code>conda install ipykernel -y</code></pre>

<h3>Step 3: Register the Kernel</h3>

<p>After installing <code>ipykernel</code>, register the environment as a Jupyter kernel using the commands below:</p>

<p>For <strong>Big_Hand_notebook_adapted</strong>:</p>
<pre><code>python -m ipykernel install --user --name=hydrosar --display-name="Hydrosar"</code></pre>

<p>For <strong>ASF_Flood_mapping</strong>:</p>
<pre><code>python -m ipykernel install --user --name=asf-jupyter-notebook --display-name="SAR Flooding"</code></pre>

<p>This setup will allow you to select the appropriate kernel to run with your notebook from within Jupyter.</p>
