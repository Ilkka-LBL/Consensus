import os
import glob

# Set paths for the modules and the docs
MODULES_PATH = os.path.join('Consensus', '*.py')
DOCS_PATH = os.path.join('docs', 'source')
MODULES_RST = os.path.join(DOCS_PATH, 'modules.rst')
INDEX_RST = os.path.join(DOCS_PATH, 'index.rst')

def create_rst_file(module_name):
    """Create an RST file for a given module."""
    rst_file_name = f"{module_name}.rst"
    rst_file_path = os.path.join(DOCS_PATH, rst_file_name)

    with open(rst_file_path, 'w') as f:
        f.write(f"{module_name}\n")
        f.write("=" * len(module_name) + "\n\n")
        f.write(f".. automodule:: Consensus.{module_name}\n")
        f.write("   :members:\n")
        f.write("   :undoc-members:\n")
        f.write("   :show-inheritance:\n")

def update_modules_rst(module_names):
    """Update modules.rst with the new module names."""
    with open(MODULES_RST, 'w') as f:
        f.write("Consensus\n")
        f.write("=========\n\n")
        f.write(".. toctree::\n")
        f.write("   :maxdepth: 4\n")
        f.write("   :caption: Contents:\n\n")
        for name in module_names:
            f.write(f"   {name}\n")

def update_index_rst():
    """Update index.rst to include modules.rst."""
    with open(INDEX_RST, 'w') as f:
        f.write("Welcome to Consensus's documentation!\n")
        f.write("=" * 40 + "\n\n")
        f.write(".. toctree::\n")
        f.write("   :maxdepth: 2\n")
        f.write("   :caption: Contents:\n\n")
        f.write("   modules\n\n")
        f.write("Indices and tables\n")
        f.write("==================\n\n")
        f.write("* :ref:`genindex`\n")
        f.write("* :ref:`modindex`\n")
        f.write("* :ref:`search`\n")

def main():
    # Find all Python modules in the Consensus directory
    module_files = glob.glob(MODULES_PATH)
    module_names = [os.path.splitext(os.path.basename(m))[0] for m in module_files]

    # Create RST files for each module
    for module in module_names:
        create_rst_file(module)

    # Update modules.rst and index.rst
    update_modules_rst(module_names)
    update_index_rst()

    print("Sphinx documentation files have been generated and updated.")

if __name__ == "__main__":
    main()
